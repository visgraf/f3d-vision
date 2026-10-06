"""North Star-1d: controller-phase cross-target measurement memory (run order, truth boundary, process contract).

Contract: docs/north-star/ns1d-cross-target-measurement-memory-contract.md.

    .venv/bin/python tools/north_star/ns1d_run.py source        --run RUN
    .venv/bin/python tools/north_star/ns1d_run.py synthetic     --run RUN
    .venv/bin/python tools/north_star/ns1d_run.py known-answer  --run RUN
    .venv/bin/python tools/north_star/ns1d_run.py events        --run RUN
    .venv/bin/python tools/north_star/ns1d_run.py replay        --run RUN    # event 0, then NS1c2 steps 0..7
    .venv/bin/python tools/north_star/ns1d_run.py visualize     --run RUN --visuals VIS

Every canonical stage runs once, from a clean pushed commit, under the accepted ``nb1a_guard.OpenGuard`` allowlist and
the accepted ``NoProcessGuard`` (no process can start, so no Blender, no render, no acquisition).  Policy code runs under
the NS1c2 gate guard in phase NORMAL (``final_look_gate_v1`` refused).  ``--dev`` runs on a scratch run only.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import glob
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

import numpy as np

sys.dont_write_bytecode = True   # a guarded stage must never write outside its declared output (no .pyc caches)

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _p in (HERE, HERE.parent, HERE.parent / "active_bootstrap", HERE.parent / "natural_bootstrap", REPO):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import ns1d_spec as SP  # noqa: E402
from nb1a_guard import OpenGuard  # noqa: E402  (accepted, read-only)

PREFIX = "[ns1d]"
TRUTH_CLASSES = {
    "ORACLE INPUT": "the frozen truth-stripped PERFECT correspondence products and the local ORACLE SEGMENTATION AID "
                    "attachments of the nine controller-phase observations (NS1b, NS1c, NS1c2 runs), read as frozen "
                    "products; no reference observation is opened by any NS1d stage",
    "DERIVED": "the event list, the memory patches, the instance measurement memory, the M0 / M1 / M2 geometries, "
               "revisions, NORMAL probes, statuses and decisions, the map re-fusions and the replay states",
    "ACCEPTED HISTORICAL REFERENCE": "the accepted Controller-01 saved patches, trajectories, final effective "
                                     "geometries, maps and object 109's own looks, and the accepted Controller-02 "
                                     "events / final residue, used only by the known-answer stage",
}


# ------------------------------------------------------------------ plumbing
def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, data) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=1, sort_keys=True, allow_nan=False) + "\n")


def read_json(path):
    return json.loads(Path(path).read_text())


def load_npz(path: Path) -> dict:
    with np.load(path, allow_pickle=False) as z:
        return {k: np.asarray(z[k]) for k in z.files}


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()


def code_state() -> dict:
    head = git("rev-parse", "HEAD")
    dirty = bool(git("status", "--porcelain", "--untracked-files=no")
                 or git("status", "--porcelain", "--", "tools", "docs", "fov3d", "scripts"))
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    try:
        pushed = git("rev-parse", f"origin/{branch}") == head
    except subprocess.CalledProcessError:
        pushed = False
    return {"commit": head, "dirty": dirty, "branch": branch, "pushed": pushed}


def utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


class Ctx:
    def __init__(self, run: Path, dev: bool) -> None:
        self.run, self.dev = run.resolve(), dev
        if dev and self.run == SP.RUN_DEFAULT.resolve():
            raise SystemExit(f"{PREFIX} STOP --dev never runs on the canonical RUN")

    def p(self, rel: str) -> Path:
        return self.run / rel


def log_process(ctx: Ctx, command: str, t0: float, status: str, extra: dict | None = None) -> None:
    ctx.run.mkdir(parents=True, exist_ok=True)
    entry = {"command": command, "argv": sys.argv, "executable": sys.executable, "code": code_state(), "dev": ctx.dev,
             "finished_utc": utc(), "seconds": round(time.time() - t0, 3), "status": status, **(extra or {})}
    with open(ctx.run / "process-log.jsonl", "a") as f:
        f.write(json.dumps(entry, sort_keys=True, default=str) + "\n")


class Refused(SystemExit):
    """A precondition refusal before anything ran (logged as `refused`, not as a failed stage)."""


def require_committed(ctx: Ctx, what: str) -> dict:
    cs = code_state()
    if not ctx.dev and (cs["dirty"] or not cs["pushed"]):
        raise Refused(f"{PREFIX} REFUSED {what} runs only from a clean, pushed implementation commit: {cs}")
    return cs


def once(path: Path, what: str) -> None:
    if Path(path).exists():
        raise Refused(f"{PREFIX} REFUSED {what} exists ({path}); it is made once")


def need(path: Path, what: str) -> None:
    if not Path(path).is_file():
        raise Refused(f"{PREFIX} REFUSED {what} comes first ({path} missing)")


def forbidden(path: str) -> bool:
    return any(t in str(path) for t in SP.FORBIDDEN)


def north_star_truth(path: str) -> bool:
    return any(t in str(path) for t in SP.NORTH_STAR_TRUTH)


def no_process():
    from fov3d.experiments.classroom_oracle.controller02 import NoProcessGuard
    return NoProcessGuard()


def process_record(pg) -> dict:
    return {"guard": "fov3d.experiments.classroom_oracle.controller02.NoProcessGuard", "events": list(pg.EVENTS),
            "attempts": list(pg.attempts)}


def guard_record(g: OpenGuard, pg=None, extra: dict | None = None) -> dict:
    rec = g.record()
    rec["modules_loaded"] = {m: m in sys.modules for m in ("cv2", "fsg_stereo", "ab1a_stereo", "ab1d_match",
                                                           "ab1d3_sgbm", "ab1b_oracle", "ab1b_geometry",
                                                           "ns1c2_render", "ns1a_render", "ns1b_render")}
    rec["violations_count"] = len(rec["violations"])
    opened = sorted({e["path"] for e in rec["events"] if e.get("event") == "open"})
    rec["forbidden_reads"] = [p for p in opened if forbidden(p)]
    rec["north_star_truth_reads"] = [p for p in opened if north_star_truth(p)]
    rec["process_guard"] = process_record(pg) if pg is not None else None
    rec.update(extra or {})
    return rec


def ns1c2(rel: str) -> Path:
    return SP.NS1C2_RUN / rel


def manifest(run_dir: Path, pin: str) -> dict:
    if sha256(run_dir / "manifest.json") != pin:
        raise SystemExit(f"{PREFIX} STOP the manifest of {run_dir.name} is not the pinned one")
    return read_json(run_dir / "manifest.json")


def verify_in_manifest(run_dir: Path, man: dict, rels) -> dict:
    out, bad = {}, []
    for rel in rels:
        h = sha256(run_dir / rel)
        if man["files"].get(rel) != h:
            bad.append(rel)
        out[rel] = h
    if bad:
        raise SystemExit(f"{PREFIX} STOP files of {run_dir.name} differ from its pinned manifest: {bad[:5]}")
    return out


def manifest_entries(man: dict, rels) -> dict:
    """Pinned hashes of array products, taken from their run's pinned manifest without opening them (their bytes are
    verified against these hashes when the replay consumes them)."""
    missing = [rel for rel in rels if rel not in man["files"]]
    if missing:
        raise SystemExit(f"{PREFIX} STOP products absent from the pinned manifest: {missing[:5]}")
    return {rel: man["files"][rel] for rel in rels}


def upstream():
    """The three pinned upstream manifests (NS1b, NS1c, NS1c2)."""
    return {"ns1b": (SP.NS1B_RUN, manifest(SP.NS1B_RUN, SP.NS1B_MANIFEST_SHA256)),
            "ns1c": (SP.NS1C_RUN, manifest(SP.NS1C_RUN, SP.NS1C_MANIFEST_SHA256)),
            "run": (SP.NS1C2_RUN, manifest(SP.NS1C2_RUN, SP.NS1C2_MANIFEST_SHA256))}


def split_ref(ref: str) -> tuple[str, str]:
    scheme, rel = ref.split(":", 1)
    return scheme, rel.rstrip("/")


# ------------------------------------------------------------------ source
def ns1c_state() -> dict:
    files = git("ls-files").split("\n")
    hits = [f for f in files if f.endswith(".md") and (REPO / f).is_file()
            and SP.NS1C_ACCEPTED_MARKER in (REPO / f).read_text(errors="replace")]
    anc = {ref: subprocess.run(["git", "merge-base", "--is-ancestor", SP.NS1C_REPORT_HEAD, ref], cwd=REPO).returncode == 0
           for ref in ("HEAD", "origin/main")}
    return {"accepted_marker_files": hits, "ns1c_report_head_ancestor_of": anc, "ok": not hits and not any(anc.values())}


def source(ctx: Ctx) -> dict:
    run = ctx.run
    once(run / "source/source-manifest.json", "the source record")
    cs = require_committed(ctx, "source")
    origin = git("remote", "get-url", "origin")
    anc = {name: subprocess.run(["git", "merge-base", "--is-ancestor", sha, "HEAD"], cwd=REPO).returncode == 0
           for name, sha in (("base", SP.BASE_COMMIT), ("ns1c2_acceptance", SP.NS1C2_ACCEPTANCE),
                             ("ns1b_acceptance", SP.NS1B_ACCEPTANCE), ("ns1a_acceptance", SP.NS1A_ACCEPTANCE),
                             ("contract", SP.CONTRACT_COMMIT))}
    contract_unchanged = subprocess.run(["git", "diff", "--quiet", SP.CONTRACT_COMMIT, "--", SP.CONTRACT],
                                        cwd=REPO).returncode == 0
    memory_unchanged = subprocess.run(["git", "diff", "--quiet", SP.BASE_COMMIT, "--",
                                       "fov3d/reconstruction/measurement_memory.py"], cwd=REPO).returncode == 0
    fov3d_unchanged = subprocess.run(["git", "diff", "--quiet", SP.BASE_COMMIT, "--", "fov3d"], cwd=REPO).returncode == 0
    ns1c2_report_at_base = git("show", f"{SP.BASE_COMMIT}:docs/north-star/ns1c2-controller02-phase-semantics-report.md")
    ns1c2_accepted = SP.NS1C2_ACCEPTED_MARKER in ns1c2_report_at_base and "**Status: ACCEPTED.**" in ns1c2_report_at_base
    decision = ns1c_state()
    if not (SP.CANONICAL_REMOTE in origin and all(anc.values()) and contract_unchanged and memory_unchanged
            and fov3d_unchanged and ns1c2_accepted and decision["ok"]):
        raise SystemExit(f"{PREFIX} STOP provenance: origin {origin}; ancestors {anc}; contract unchanged "
                         f"{contract_unchanged}; memory unchanged {memory_unchanged}; fov3d unchanged {fov3d_unchanged}; "
                         f"NS1c2 accepted {ns1c2_accepted}; NS1c {decision}")
    c01_files = sorted(glob.glob(str(SP.C01_RUN / SP.C01_TRAJECTORY_GLOB)))
    reads = ([SP.NS1B_RUN / "manifest.json", SP.NS1C_RUN / "manifest.json", ns1c2("manifest.json"),
              ns1c2("check-summary.json"), ns1c2("freeze/scene-freeze.json")]
             + [SP.C02_RUN / f for f in SP.C02_PINS] + c01_files)
    (run / "source").mkdir(parents=True, exist_ok=True)
    g = OpenGuard("ns1d-source", reads, [run / "source"])
    pg = no_process()
    try:
        with g, pg:
            pins = {p: sha256(REPO / p) for p in SP.SOURCE_PINS}
            bad = {p: h for p, h in pins.items() if h != SP.SOURCE_PINS[p]}
            if bad:
                raise SystemExit(f"{PREFIX} STOP accepted sources changed: {bad}")
            ups = upstream()
            if sha256(ns1c2("check-summary.json")) != SP.NS1C2_CHECK_SUMMARY_SHA256 or \
                    read_json(ns1c2("check-summary.json"))["marker"] != "NORTH_STAR1C2_CHECKS_PASS":
                raise SystemExit(f"{PREFIX} STOP the NS1c2 check summary is not the pinned passing one")
            if sha256(ns1c2("freeze/scene-freeze.json")) != SP.NS1C2_SCENE_FREEZE_SHA256:
                raise SystemExit(f"{PREFIX} STOP the NS1c2 scene freeze is not the pinned one")
            c02 = {f: sha256(SP.C02_RUN / f) for f in SP.C02_PINS}
            lines = "".join(f"{Path(f).relative_to(SP.C01_RUN)} {sha256(f)}\n" for f in c01_files)
            c01_digest = hashlib.sha256(lines.encode()).hexdigest()
            if c02 != SP.C02_PINS or c01_digest != SP.C01_TRAJECTORY_DIGEST or len(c01_files) != SP.C01_TRAJECTORY_COUNT:
                raise SystemExit(f"{PREFIX} STOP the accepted Controller-01 / 02 history pins differ")
            out = {"schema": "NS1d-source-v1", "experiment": SP.EXPERIMENT, "code": cs, "origin": origin,
                   "ancestors": anc, "contract": SP.CONTRACT, "contract_commit": SP.CONTRACT_COMMIT,
                   "contract_unchanged": contract_unchanged, "base_commit": SP.BASE_COMMIT,
                   "ns1c2_acceptance": SP.NS1C2_ACCEPTANCE, "ns1c2_accepted_on_base": ns1c2_accepted,
                   "ns1c_decision": decision, "measurement_memory_unchanged_since_base": memory_unchanged,
                   "fov3d_unchanged_since_base": fov3d_unchanged, "source_pins": pins,
                   "upstream_manifests": {k: {"run": str(v[0]), "files": len(v[1]["files"])} for k, v in ups.items()},
                   "ns1c2_check_summary": SP.NS1C2_CHECK_SUMMARY_SHA256,
                   "ns1c2_scene_freeze": SP.NS1C2_SCENE_FREEZE_SHA256,
                   "history": {"controller02": c02, "controller01_trajectories": len(c01_files),
                               "controller01_trajectory_digest": c01_digest},
                   "memory_class": "fov3d.reconstruction.measurement_memory.InstanceMeasurementMemory (unchanged)",
                   "scheduler": "fov3d.control.controller02.schedule_normal via ns1c2_phase.SceneMachine (unchanged)"}
            write_json(run / "source/source-manifest.json", out)
    finally:
        write_json(run / "source/source-opened-files.json", guard_record(g, pg))
    return {"pins": len(pins), "ns1c2_accepted": ns1c2_accepted, "ns1c_not_accepted": decision["ok"]}


# ------------------------------------------------------------------ synthetic known answers
def synthetic(ctx: Ctx) -> dict:
    run = ctx.run
    need(run / "source/source-manifest.json", "source")
    once(run / "synthetic/synthetic-report.json", "the synthetic known answers")
    require_committed(ctx, "synthetic")
    import ns1d_synthetic as SY
    (run / "synthetic").mkdir(parents=True, exist_ok=True)
    pg = no_process()
    with pg:
        rep = SY.run_all()
    rep["process_guard"] = process_record(pg)
    write_json(run / "synthetic/synthetic-report.json", rep)
    if rep["failed"]:
        raise SystemExit(f"{PREFIX} STOP synthetic known answers failed: {rep['failed']}")
    return {"passed": rep["count"] - len(rep["failed"]), "count": rep["count"], "marker": rep["marker"]}


# ------------------------------------------------------------------ the historical known answer
def known_answer(ctx: Ctx) -> dict:
    run = ctx.run
    rep = read_json(run / "synthetic/synthetic-report.json") if (run / "synthetic/synthetic-report.json").exists() else {}
    if rep.get("failed") != []:
        raise Refused(f"{PREFIX} REFUSED the synthetic known answers must pass first")
    once(run / "known-answer/known-answer.json", "the historical known answer")
    cs = require_committed(ctx, "known-answer")
    import ns1b_chart as CH
    import ns1b_core as B
    import ns1b_fixtures as FX
    import ns1c2_phase as PH
    import ns1c2_synthetic as SY2
    import ns1d_core as K
    from fov3d.control import controller02 as c2, integrated as ic
    from fov3d.reconstruction.measurement_memory import InstanceMeasurementMemory, effective_target_geometry
    CH.ensure_policy_modules()
    import fsg6f_frontier  # noqa: F401
    traj_files = FX.trajectory_files()                         # listed outside the guard (no directory listing inside)
    objs = sorted(int(f.parent.name.split("_")[1]) for f in traj_files)
    rows_pre = []
    for f in traj_files:
        for t in json.loads(f.read_text()):
            rows_pre.append((int(f.parent.name.split("_")[1]), int(t["step"])))
    patch_files = sorted({SP.C01_RUN / f"objects/instance_{i:04d}/patches/fix_{k:02d}.npz" for i, k in rows_pre})
    obj = SP.HISTORICAL_109["object"]
    own = [k for i, k in rows_pre if i == obj]
    acq = [SP.C01_RUN / f"objects/instance_{obj:04d}/acquisitions/fix_{k:02d}/{n}" for k in own
           for n in ("calibration.json", "oracle_observation.npz")]
    finals = [SP.C01_RUN / f"objects/instance_{i:04d}/{n}" for i in objs for n in ("final_effective_geometry.npz",
                                                                                 "final_map.npz")]
    reads = list(traj_files) + patch_files + acq + finals + [SP.C02_RUN / f for f in SP.C02_PINS]
    (run / "known-answer").mkdir(parents=True, exist_ok=True)
    g = OpenGuard("ns1d-known-answer", reads, [run / "known-answer"])
    pg = no_process()
    try:
        with g, pg:
            lines = "".join(f"{Path(f).relative_to(SP.C01_RUN)} {sha256(f)}\n" for f in traj_files)
            if hashlib.sha256(lines.encode()).hexdigest() != SP.C01_TRAJECTORY_DIGEST or \
                    {f: sha256(SP.C02_RUN / f) for f in SP.C02_PINS} != SP.C02_PINS:
                raise SystemExit(f"{PREFIX} STOP the accepted history pins differ")
            rows = FX.c01_rows(traj_files)
            # -- 1. the accepted Controller-01 memory rebuilt from its 141 saved patches
            mem = InstanceMeasurementMemory()
            mismatches, per_look = [], []
            for r in rows:
                i, k, s = int(r["target_id"]), int(r["step"]), int(r["global_step"])
                patch = load_npz(SP.C01_RUN / f"objects/instance_{i:04d}/patches/fix_{k:02d}.npz")
                add = mem.append_patch(patch, source_global_index=s, source_active_target_id=i)
                logged = {int(a): int(b) for a, b in r["measurement_memory_additions"].items()}
                if add != logged:
                    mismatches.append(s)
                per_look.append([s, i, sum(add.values())])
            ids = mem.instance_ids()
            total = 0
            own_pts = cross_pts = 0
            unloc = {}
            per_obj, geo_bad, prov_bad = {}, [], []
            for iid in ids:
                snap = mem.snapshot(iid)
                total += len(snap.xyz_h)
                if iid in objs:
                    o = int((snap.source_active_target_id == iid).sum())
                    own_pts += o
                    cross_pts += len(snap.xyz_h) - o
                    per_obj[str(iid)] = {"own": o, "cross": int(len(snap.xyz_h) - o)}
                else:
                    unloc[str(iid)] = int(len(snap.xyz_h))
            for iid in objs:
                feg = load_npz(SP.C01_RUN / f"objects/instance_{iid:04d}/final_effective_geometry.npz")
                fm = load_npz(SP.C01_RUN / f"objects/instance_{iid:04d}/final_map.npz")
                snap = mem.snapshot(iid)
                if not (np.array_equal(feg["measured_source_global_index"], snap.source_global_index)
                        and np.array_equal(feg["measured_source_active_target_id"], snap.source_active_target_id)):
                    prov_bad.append(iid)
                eff = effective_target_geometry(np.asarray(fm["xyz_h"], np.float64), snap.xyz_h).astype(np.float32)
                if not (eff.shape == feg["xyz_h"].shape and np.array_equal(eff, feg["xyz_h"])
                        and int(feg["active_map_points"]) == len(fm["xyz_h"])
                        and np.array_equal(eff[:len(fm["xyz_h"])], fm["xyz_h"])):
                    geo_bad.append(iid)
            hm = SP.HISTORICAL_MEMORY
            memory_rebuild = {
                "looks": len(rows), "addition_mismatches": mismatches, "total_points": total,
                "observed_instances": len(ids), "localized_objects": len(objs), "own_target_points": own_pts,
                "cross_target_points": cross_pts,
                "cross_fraction_pct": round(100.0 * cross_pts / max(1, own_pts + cross_pts), 1),
                "unlocated_measured_ids": len(unloc), "unlocated_points": int(sum(unloc.values())),
                "unlocated": unloc, "per_object": per_obj, "final_provenance_mismatches": prov_bad,
                "final_effective_geometry_mismatches": geo_bad,
                "statement": "the accepted InstanceMeasurementMemory rebuilt from the 141 saved name-free oracle patches "
                             "in global-step order; effective_target_geometry(final map, snapshot) equals every saved "
                             "final effective geometry (map first, measured second, duplicates retained)"}
            memory_rebuild["ok"] = bool(
                not mismatches and len(rows) == hm["looks"] and total == hm["total_points"]
                and len(ids) == hm["observed_instances"] and len(objs) == hm["localized_objects"]
                and own_pts == hm["own_target_points"] and cross_pts == hm["cross_target_points"]
                and memory_rebuild["cross_fraction_pct"] == hm["cross_fraction_pct"]
                and len(unloc) == hm["unlocated_measured_ids"] and sum(unloc.values()) == hm["unlocated_points"]
                and not prov_bad and not geo_bad)
            del mem
            # -- 2. the 109 reactivation, replayed with the accepted routine (ns1b_fixtures.rebuild)
            _FR, _PUB, c01, _c02x, _EP = FX._modules()
            h = SP.HISTORICAL_109
            before = FX.rebuild(obj, h["quiet_step"], rows)
            after = FX.rebuild(obj, h["reactivated_after_step"], rows)
            res_b, _dec_b = c01.probe_local_policy(before["ctx"], before["geometry"])
            res_a, _dec_a = c01.probe_local_policy(after["ctx"], after["geometry"])
            ev = read_json(SP.C02_RUN / "events.json")["events"]
            quiet_ev = next(e for e in ev if e["event"] == "quiet" and int(e["object"]) == obj
                            and int(e["global_step"]) == h["quiet_step"])
            react_ev = next(e for e in ev if e["event"] == "natural_reactivation" and int(e["object"]) == obj)
            sb, sa = K.jsonable(dict(res_b.detail)), K.jsonable(dict(res_a.detail))
            d_quiet = B.compare(quiet_ev["probe"], sb, 0.0, "quiet")
            d_before = B.compare(react_ev["probe_before"], sb, 0.0, "probe_before")
            d_after = B.compare(react_ev["probe_after"], sa, 0.0, "probe_after")
            mem7 = InstanceMeasurementMemory()
            for r in rows:
                if int(r["global_step"]) > h["reactivated_after_step"]:
                    break
                mem7.append_patch(load_npz(SP.C01_RUN / f"objects/instance_{int(r['target_id']):04d}/patches/"
                                                        f"fix_{int(r['step']):02d}.npz"),
                                  source_global_index=int(r["global_step"]), source_active_target_id=int(r["target_id"]))
            s7 = mem7.snapshot(obj)
            new = s7.source_global_index > h["quiet_step"]
            added = {"points": int(new.sum()), "source_targets": sorted({int(v) for v in s7.source_active_target_id[new]}),
                     "source_global_steps": sorted({int(v) for v in s7.source_global_index[new]})}
            map_b = np.asarray(before["ctx"].surface_map.xyz_h)
            map_a = np.asarray(after["ctx"].surface_map.xyz_h)
            # the accepted adapter: 109 QUIET (cached at its revision), 110 current; the revision change invalidates the
            # cached quiet probe and the refresh emits natural_reactivation (no reactivation call exists)
            v, f = c01.VERGENCE, c01.FOCUS
            state = {"phase": "before"}
            calls = {obj: 0, h["trigger"]: 0}

            def probe(i):
                calls[i] += 1
                if i == obj:
                    return res_b if state["phase"] == "before" else res_a
                return ic.ProbeResult(ic.Observe(i, (0.0, 0.0), v, f, "fsg6f"), {"stub": "actionable"})

            def rev(i):
                if i == obj:
                    return tuple(before["revision"] if state["phase"] == "before" else after["revision"])
                return (1, 0)
            m = PH.SceneMachine([obj, h["trigger"]], budget=24, vergence=v, focus=f)
            with PH.GateGuard(c2.ScenePhase.NORMAL.value, "known-answer: 109 re-drive") as gg:
                quiet_ids = K.resume_scene(m, {obj: h["own_looks"], h["trigger"]: 2}, current=h["trigger"], bout=1,
                                           step=h["reactivated_after_step"], probe=probe, revision=rev,
                                           quiet_since=h["quiet_step"])
                plan = m.decide(K.refuse_gate)
                n_ev = len(m.events)
                calls_before_commit = dict(calls)
                m_null = PH.SceneMachine.from_json(m.to_json())
                null_events = []
                m_null.on_event = null_events.append
                m_null.commit(plan, ic.ObservationOutcome(initialized=None, record={}), probe, rev)  # revision unchanged
                state["phase"] = "after"
                m.commit(plan, ic.ObservationOutcome(initialized=None, record={}), probe, rev)
            evs = m.events[n_ev:]
            re = [e for e in evs if e["event"] == "natural_reactivation"]
            redrive = {"quiet_at_resume": quiet_ids, "plan": {"target": plan["target_id"], "decision": plan["decision"]},
                       "null_commit_events": [[e["event"], e["object"]] for e in null_events],
                       "probe_calls_109": {"before_commit": calls_before_commit[obj], "after_commit": calls[obj]},
                       "events": [[e["event"], e["object"], e.get("trigger_target")] for e in evs],
                       "reactivation_probe_before_equal": bool(re) and not B.compare(react_ev["probe_before"],
                                                                                     K.jsonable(re[0]["probe_before"]),
                                                                                     0.0),
                       "reactivation_probe_after_equal": bool(re) and not B.compare(react_ev["probe_after"],
                                                                                    K.jsonable(re[0]["probe_after"]),
                                                                                    0.0),
                       "gate_guard": gg.record()}
            redrive["ok"] = bool(quiet_ids == [obj] and plan["target_id"] == h["trigger"] and not null_events
                                 and len(re) == 1 and re[0]["trigger_target"] == h["trigger"]
                                 and redrive["reactivation_probe_before_equal"]
                                 and redrive["reactivation_probe_after_equal"]
                                 and calls[obj] == calls_before_commit[obj] + 1 and gg.record()["calls"] == 0)
            reactivation = {
                "object": obj, "revision_before": before["revision"], "revision_after": after["revision"],
                "own_looks": [len(before["ctx"].visited), len(after["ctx"].visited)],
                "map_unchanged": bool(map_b.shape == map_a.shape and np.array_equal(map_b, map_a)),
                "effective_points": [int(len(before["geometry"])), int(len(after["geometry"]))],
                "added_since_quiet": added, "state_before": res_b.state.value, "state_after": res_a.state.value,
                "summary_before": sb, "summary_after": sa,
                "differences_vs_accepted_quiet_event": d_quiet[:5],
                "differences_vs_accepted_probe_before": d_before[:5],
                "differences_vs_accepted_probe_after": d_after[:5],
                "proposal_after": None if res_a.action is None else list(res_a.action.gaze_yaw_pitch_deg),
                "adapter_redrive": redrive}
            reactivation["ok"] = bool(
                before["revision"][0] == after["revision"][0] == h["own_looks"]
                and after["revision"][1] - before["revision"][1] == h["cross_points_added"]
                and added == {"points": h["cross_points_added"], "source_targets": [h["trigger"]],
                              "source_global_steps": [h["reactivated_after_step"]]}
                and reactivation["map_unchanged"] and tuple(reactivation["effective_points"]) == h["effective_points"]
                and res_b.state.value == "QUIET" and res_a.state.value == "ACTIONABLE"
                and not d_quiet and not d_before and not d_after
                and reactivation["proposal_after"] == list(h["proposal_after_deg"]) and redrive["ok"])
            # -- 3. the scheduler: the accepted Controller-02 history re-driven (unchanged NS1c2 routine)
            traj = {int(Path(f).parent.name.split("_")[1]): read_json(f) for f in traj_files}
            fres = read_json(SP.C02_RUN / "final-residue.json")
            with PH.GateGuard(c2.ScenePhase.NORMAL.value, "known-answer: historical trace") as gh:
                hist = SY2.historical_trace(traj, ev, fres, 24)
            h_ok, h_checks = SY2.historical_ok(hist)
            serviced = [a for a in hist["action_sequence"] if a[1] == obj and a[0] == h["serviced_at_step"]]
            scheduler = {"historical_ok": h_ok, "checks": h_checks,
                         "natural_reactivation_switches": hist["natural_reactivation_switches"],
                         "service_of_109": serviced, "gate_guard": gh.record()}
            scheduler["ok"] = bool(h_ok and serviced and serviced[0][4] == h["service_reason"]
                                   and hist["natural_reactivation_switches"] == hm["natural_reactivations"])
            out = {"schema": "NS1d-known-answer-v1", "truth": SP.TRUTH_HISTORICAL, "code": cs,
                   "role": "ACCEPTED HISTORICAL REFERENCE known answers (not NS1d measurements)",
                   "memory_rebuild": memory_rebuild, "reactivation_109": reactivation, "scheduler": scheduler,
                   "files_read_by_ns1b_fixtures": len(FX.FILES_READ),
                   "ok": bool(memory_rebuild["ok"] and reactivation["ok"] and scheduler["ok"])}
            write_json(run / "known-answer/known-answer.json", out)
    finally:
        write_json(run / "known-answer/known-answer-opened-files.json", guard_record(g, pg))
    if not out["ok"]:
        raise SystemExit(f"{PREFIX} STOP the historical known answer failed: memory {memory_rebuild['ok']}, "
                         f"reactivation {reactivation['ok']}, scheduler {scheduler['ok']}")
    return {"memory": memory_rebuild["ok"], "reactivation_109": reactivation["ok"], "scheduler": scheduler["ok"],
            "total_points": memory_rebuild["total_points"], "cross_fraction_pct": memory_rebuild["cross_fraction_pct"]}


# ------------------------------------------------------------------ the frozen event list (records only)
def event_sources() -> list[dict]:
    """The controller-phase physical observations as the accepted records name them (NS1b action, NS1c2 steps)."""
    out = [{"event": 0, "source": "NS1b action 1", "ns1c2_step": None, "observation": "ns1b:", "accepted_target_map":
            "ns1b:fusion/fused-target-map.npz", "fusion": "ns1b:fusion/fusion.json",
            "target_patch": "ns1b:fusion/target-patch.npz"}]
    for k in range(SP.NS1C2_STEPS):
        out.append({"event": k + 1, "source": f"NS1c2 step {k}", "ns1c2_step": k,
                    "observation": None,      # read from the step's fusion record
                    "decision": f"run:steps/step-{k:02d}/plan/decision.json",
                    "fusion": f"run:steps/step-{k:02d}/fusion/fusion.json",
                    "target_patch": f"run:steps/step-{k:02d}/fusion/target-patch.npz",
                    "accepted_target_map": f"run:steps/step-{k:02d}/fusion/fused-target-map.npz"})
    return out


def root_of(scheme: str) -> Path:
    return {"ns1b": SP.NS1B_RUN, "ns1c": SP.NS1C_RUN, "run": SP.NS1C2_RUN}[scheme]


def ref_path(ref: str) -> Path:
    scheme, rel = split_ref(ref)
    return root_of(scheme) / rel if rel else root_of(scheme)


def events(ctx: Ctx) -> dict:
    run = ctx.run
    ka = read_json(run / "known-answer/known-answer.json") if (run / "known-answer/known-answer.json").exists() else {}
    if not ka.get("ok"):
        raise Refused(f"{PREFIX} REFUSED the historical known answer must pass first")
    once(run / "events/event-list.json", "the event list")
    cs = require_committed(ctx, "events")
    srcs = event_sources()
    jsons = [ns1c2("scene/final-scene-state.json"), ns1c2("manifest.json"), SP.NS1B_RUN / "manifest.json",
             SP.NS1C_RUN / "manifest.json"]
    for s in srcs:
        jsons += [ref_path(s["fusion"])] + ([ref_path(s["decision"])] if s.get("decision") else [])
    # observation roots are known only from the fusion records: read them first (outside no file but the records)
    obs_roots = {0: "ns1b:"}
    for s in srcs[1:]:
        obs_roots[s["event"]] = read_json(ref_path(s["fusion"]))["observation_source"]
    for e, ref in obs_roots.items():
        root = ref_path(ref)
        jsons += [root / f for f in SP.FREEZE_FILES] + [root / "observation/acquisition/calibration.json",
                                                        root / "segmentation/identity-summary.json"]
    (run / "events").mkdir(parents=True, exist_ok=True)
    (run / "freeze").mkdir(parents=True, exist_ok=True)
    g = OpenGuard("ns1d-events", jsons, [run / "events", run / "freeze"])
    pg = no_process()
    problems = []
    try:
        with g, pg:
            ups = upstream()
            final = read_json(ns1c2("scene/final-scene-state.json"))
            verify_in_manifest(SP.NS1C2_RUN, ups["run"][1], ["scene/final-scene-state.json"])
            if int(final["executed_actions"]) != SP.NS1C2_STEPS or not final["stopped"] or \
                    int(final["stop"]["global_step"]) != SP.NS1C2_STEPS - 1:
                problems.append("the accepted NS1c2 trace is not 8 executed actions ending with the stop at step 7")
            rows = []
            for s in srcs:
                e = s["event"]
                scheme, base = split_ref(obs_roots[e])
                root = ref_path(obs_roots[e])
                run_dir, man = ups[scheme]
                prefix = (base + "/") if base else ""
                fu_scheme, fu_rel = split_ref(s["fusion"])
                verify_in_manifest(ups[fu_scheme][0], ups[fu_scheme][1],
                                   [fu_rel] + ([split_ref(s["decision"])[1]] if s.get("decision") else []))
                arrays = manifest_entries(ups[fu_scheme][1], [split_ref(s[k])[1] for k in ("target_patch",
                                                                                         "accepted_target_map")])
                fu = read_json(ref_path(s["fusion"]))
                obs_h = verify_in_manifest(run_dir, man, [prefix + f for f in SP.FREEZE_FILES]
                                           + [prefix + "observation/acquisition/calibration.json",
                                              prefix + "segmentation/identity-summary.json"])
                obs_h.update(manifest_entries(man, [prefix + f for f in SP.OBS_FILES]))
                cfz = read_json(root / "freeze/correspondence-freeze.json")
                gfz = read_json(root / "freeze/geometry-freeze.json")
                if (cfz["files"].get("correspondence/oracle-correspondences.npz")
                        != obs_h[prefix + "correspondence/oracle-correspondences.npz"]
                        or gfz["files"].get("geometry/epipolar-result.npz") != obs_h[prefix + "geometry/epipolar-result.npz"]):
                    problems.append(f"event {e}: the frozen correspondence / geometry products differ from the manifest")
                cal = read_json(root / "observation/acquisition/calibration.json")
                ofz = read_json(root / "freeze/observation-freeze.json")
                if ofz["files"]["observation/acquisition/calibration.json"] != obs_h[
                        prefix + "observation/acquisition/calibration.json"]:
                    problems.append(f"event {e}: the calibration is not the frozen one")
                idsum = read_json(root / "segmentation/identity-summary.json")
                target = int(fu["target"])
                row = {"event": e, "source": s["source"], "ns1c2_step": s["ns1c2_step"], "target": target,
                       "patch_id": fu["patch_id"], "observation_root": obs_roots[e],
                       "world_gaze_deg": [float(v) for v in cal["gaze_yaw_pitch_deg"]],
                       "observation_freeze_sha256": obs_h[prefix + "freeze/observation-freeze.json"],
                       "correspondence_freeze_sha256": obs_h[prefix + "freeze/correspondence-freeze.json"],
                       "geometry_freeze_sha256": obs_h[prefix + "freeze/geometry-freeze.json"],
                       "calibration_sha256": obs_h[prefix + "observation/acquisition/calibration.json"],
                       "products": {f: obs_h[prefix + f] for f in SP.OBS_FILES},
                       "fusion": s["fusion"], "target_patch": s["target_patch"],
                       "accepted_target_map": s["accepted_target_map"],
                       "accepted_target_map_sha256": arrays[split_ref(s["accepted_target_map"])[1]],
                       "target_patch_sha256": arrays[split_ref(s["target_patch"])[1]],
                       "fusion_action": fu["action"], "target_points": int(fu["measured_points"]),
                       "recorded_ids_in_view": {str(k): int(v) for k, v in idsum["entities"].items()}}
                if s.get("decision"):
                    d = read_json(ref_path(s["decision"]))
                    a = d["action"]
                    row["decision"] = s["decision"]
                    row["accepted_action"] = {"target": int(a["target"]), "source": a["source"],
                                              "local_gaze_deg": a["local_gaze_deg"],
                                              "world_gaze_deg": a["world_gaze_deg"],
                                              "scheduler": d["scheduler_decision"]["result"]["reason"]}
                    if int(a["target"]) != target or [float(v) for v in a["world_gaze_deg"]] != row["world_gaze_deg"]:
                        problems.append(f"event {e}: the decision and the observation disagree (target / H0 gaze)")
                    if int(d["global_step"]) != s["ns1c2_step"] or fu["patch_id"] != d["action"]["patch_id"]:
                        problems.append(f"event {e}: step / patch id mismatch")
                rows.append(row)
            keys = [r["observation_freeze_sha256"] for r in rows]
            cals = [r["calibration_sha256"] for r in rows]
            exp = SP.EXPECTED_EVENTS
            compare = []
            for r, x in zip(rows, exp):
                ok = (r["event"] == x["event"] and r["target"] == x["target"] and r["patch_id"] == x["patch_id"]
                      and r["ns1c2_step"] == x["ns1c2_step"] and r["observation_root"].rstrip("/") ==
                      x["observation"].rstrip("/")
                      and max(abs(a - b) for a, b in zip(r["world_gaze_deg"], x["world_gaze_deg"]))
                      <= SP.GAZE_EXPECTATION_TOL_DEG)
                compare.append({"event": r["event"], "matches_expectation": bool(ok)})
            unique = len(set(keys)) == len(keys) and len(set(cals)) == len(cals)
            match = len(rows) == len(exp) and all(c["matches_expectation"] for c in compare)
            if not unique:
                problems.append("a physical observation appears twice in the event list")
            if not match:
                problems.append("the derived event list differs from the contract expectation")
            out = {"schema": "NS1d-event-list-v1", "truth": SP.TRUTH_DERIVED, "code": cs,
                   "statement": "the UNIQUE PHYSICAL CONTROLLER-PHASE OBSERVATIONS, derived from the accepted NS1b / "
                                "NS1c2 records only (no array opened); memory event index = position in this list",
                   "scope": SP.LABEL_BOOTSTRAP, "events": rows, "count": len(rows), "unique_observations": unique,
                   "targets": [r["target"] for r in rows], "expectation": compare, "matches_expectation": match,
                   "accepted_ns1c2_executed_actions": int(final["executed_actions"]), "problems": problems}
            write_json(run / "events/event-list.json", out)
            write_json(run / "freeze/event-list-freeze.json", {
                "schema": "NS1d-event-list-freeze-v1", "truth": SP.TRUTH_DERIVED, "frozen_utc": utc(), "code": cs,
                "statement": "the event list, frozen before any memory patch is built",
                "files": {"events/event-list.json": sha256(run / "events/event-list.json")}})
    finally:
        write_json(run / "events/events-opened-files.json", guard_record(g, pg))
    if problems:
        raise SystemExit(f"{PREFIX} STOP event list: {problems}")
    return {"events": len(rows), "targets": out["targets"], "unique": unique}


# ------------------------------------------------------------------ the causal replay (B11 + B12)
CONTEXT_FIELDS = ("looks", "visited", "current_local_gaze", "own_looks", "evidence", "map", "temporary_entity_id",
                  "initialization_rank", "chart_id", "chart_sha256")


def context_part(rec: dict) -> dict:
    return {k: rec[k] for k in CONTEXT_FIELDS}


def record_reads(recs: dict) -> list[Path]:
    import ns1c2_core as C2
    out = []
    for rec in recs.values():
        for look in rec["looks"]:
            out += [C2.resolve(look["calibration"], SP.NS1C2_RUN), C2.resolve(look["state"], SP.NS1C2_RUN)]
        out += [C2.resolve(rec["evidence"]["path"], SP.NS1C2_RUN), C2.resolve(rec["map"]["path"], SP.NS1C2_RUN)]
    return out


def replay(ctx: Ctx) -> dict:
    run = ctx.run
    need(run / "freeze/event-list-freeze.json", "events")
    once(run / "replay/replay.json", "the causal replay")
    cs = require_committed(ctx, "replay")
    import ns1b_chart as CH
    import ns1b_core as B
    import ns1c2_core as C2
    import ns1c2_phase as PH
    import ns1d_core as K
    from fov3d.control import controller02 as c2, integrated as ic
    CH.ensure_policy_modules()
    import ns1a_core  # noqa: F401
    import fsg6f_frontier  # noqa: F401
    # ---- everything the stage may read (an event's arrays are opened only when that event is consumed)
    states = [ns1c2("scene/state-initial.json")] + [ns1c2(f"scene/state-after-step-{k:02d}.json")
                                                    for k in range(SP.NS1C2_STEPS)]
    all_recs = {}
    for p in states:
        for kk, rec in json.loads(p.read_text())["entities"].items():
            all_recs[f"{p.name}:{kk}"] = rec
    el = read_json(run / "events/event-list.json")
    reads = [run / "events/event-list.json", run / "freeze/event-list-freeze.json", ns1c2("charts/policy-charts.json"),
             ns1c2("manifest.json"), SP.NS1B_RUN / "manifest.json", SP.NS1C_RUN / "manifest.json"] + states
    reads += record_reads(all_recs)
    ns1c2_probe_files = sorted((SP.NS1C2_RUN / "initial-probe/probes").glob("e*.json"))
    ns1c2_fresh = {0: {int(p.stem[1:]) for p in ns1c2_probe_files}}
    for k in range(SP.NS1C2_STEPS):
        fs = sorted((SP.NS1C2_RUN / f"steps/step-{k:02d}/update/probes").glob("e*.json"))
        ns1c2_fresh[k + 1] = {int(p.stem[1:]) for p in fs}
        ns1c2_probe_files += fs
    reads += ns1c2_probe_files
    reads += [SP.NS1B_RUN / "context/target-map-H0.npz"]
    for r in el["events"]:
        root = ref_path(r["observation_root"])
        reads += [root / f for f in SP.OBS_FILES]
        reads += [ref_path(r["target_patch"]), ref_path(r["accepted_target_map"]), ref_path(r["fusion"])]
        if r.get("decision"):
            reads.append(ref_path(r["decision"]))
    for sub in ("replay", "freeze"):
        (run / sub).mkdir(parents=True, exist_ok=True)
    g = OpenGuard("ns1d-replay", reads, [run / "replay", run / "freeze"])
    pg = no_process()
    out, failure = None, None
    try:
        with g, pg, PH.GateGuard(c2.ScenePhase.NORMAL.value, "ns1d replay") as gg:
            fz = read_json(run / "freeze/event-list-freeze.json")
            if sha256(run / "events/event-list.json") != fz["files"]["events/event-list.json"]:
                raise SystemExit(f"{PREFIX} STOP the event list changed after its freeze")
            ups = upstream()
            verify_in_manifest(SP.NS1C2_RUN, ups["run"][1], ["charts/policy-charts.json"]
                               + [f"scene/{p.name}" for p in states])
            chs = read_json(ns1c2("charts/policy-charts.json"))["charts"]
            st0 = read_json(states[0])
            ids = [int(i) for i in st0["scene_ids"]]
            if ids != list(SP.COHERENT):
                raise SystemExit(f"{PREFIX} STOP the scheduler identity set is not the frozen coherent set: {ids}")
            recs = {k: json.loads(json.dumps(v)) for k, v in st0["entities"].items()}
            ledger = K.MemoryLedger()
            budget = C2.budget_live()
            v, f = C2.vergence_focus()
            fresh = {m_: {} for m_ in SP.MODES}           # after-event -> {entity: probe record path}
            outs = {m_: {} for m_ in SP.MODES}            # latest probe output per mode / entity
            m1_cache: dict[int, tuple] = {}
            cur_event = {"e": 0}

            def probe_fn(mode):
                def probe(i):
                    rec = recs[str(i)]
                    rev = K.revision(mode, rec, ledger)
                    o = K.probe(mode, rec, chs[str(i)], SP.NS1C2_RUN, ledger,
                                f"{mode} probe of entity {i} after event {cur_event['e']}")
                    rel = SP.probe_rel(mode, cur_event["e"], i)
                    write_json(run / rel, {"schema": "NS1d-probe-v1", "truth": SP.TRUTH_DERIVED, "mode": mode,
                                           "entity": int(i), "after_event": cur_event["e"], "revision": rev,
                                           "gate_called": False, "probe": C2.jsonable(o),
                                           "memory": K.memory_counts(rec, ledger)})
                    fresh[mode].setdefault(cur_event["e"], {})[int(i)] = rel
                    outs[mode][int(i)] = o
                    return C2.probe_result(o, i, {"probe_path": rel, "revision": rev})
                return probe

            def rev_fn(mode):
                return lambda i: K.revision(mode, recs[str(i)], ledger)

            def m1_probe(i):
                rev = K.revision("M1", recs[str(i)], ledger)
                if i in m1_cache and m1_cache[i][0] == rev:
                    return m1_cache[i][1], False
                probe_fn("M1")(i)                 # computes and writes the M1 record
                m1_cache[i] = (rev, outs["M1"][int(i)])
                return m1_cache[i][1], True

            # ---- event consumption (one physical observation; arrays opened only here)
            event_records = {}

            def consume_event(e: int, prev_map_rec: dict | None) -> dict:
                r = el["events"][e]
                root = ref_path(r["observation_root"])
                for rel_, h in r["products"].items():
                    if sha256(root / rel_) != h:
                        raise SystemExit(f"{PREFIX} STOP event {e}: {rel_} is not the pinned product")
                prod = load_npz(root / "correspondence/oracle-correspondences.npz")
                geom = load_npz(root / "geometry/epipolar-result.npz")
                ident = load_npz(root / "segmentation/local-identity.npz")
                patch, info = K.memory_patch(prod, geom, ident)
                t = int(r["target"])
                if sha256(ref_path(r["target_patch"])) != r["target_patch_sha256"]:
                    raise SystemExit(f"{PREFIX} STOP event {e}: the accepted target patch is not the pinned one")
                tp = load_npz(ref_path(r["target_patch"]))
                subset = K.target_subset_equal(patch, prod, tp["xyz_h"], ident["temporary_entity_id"],
                                               geom["valid_epi"], t)
                if info["by_observed_id"] != r["recorded_ids_in_view"]:
                    raise SystemExit(f"{PREFIX} STOP event {e}: the ids in the patch differ from the recorded identity "
                                     "summary")
                # the accepted target-only map update, reproduced (no other map is touched)
                fu = read_json(ref_path(r["fusion"]))
                acc_map = load_npz(ref_path(r["accepted_target_map"]))
                if sha256(ref_path(r["accepted_target_map"])) != r["accepted_target_map_sha256"]:
                    raise SystemExit(f"{PREFIX} STOP event {e}: the accepted target map is not the pinned one")
                if prev_map_rec is None:        # event 0: NS1b's own pre-action map
                    sm = C2.load_map(SP.NS1B_RUN / "context/target-map-H0.npz")
                else:
                    sm = C2.load_map(C2.resolve(prev_map_rec["path"], SP.NS1C2_RUN))
                tpatch = {"frame": "H0", "patch_id": r["patch_id"], "xyz_h": tp["xyz_h"], "rgb": tp["rgb"],
                          "instance_id": tp["instance_id"], "points": int(len(tp["xyz_h"]))}
                fused, frec = B.fuse_h0(sm, tpatch, t)
                refused_equal = C2.maps_equal(B.map_arrays(fused), acc_map)
                if not (subset and refused_equal and frec["map_after"] == fu["map_after"]):
                    raise SystemExit(f"{PREFIX} STOP event {e}: target subset {subset}, re-fused map equal "
                                     f"{refused_equal} (Outcome 4)")
                key = r["observation_freeze_sha256"]
                additions = ledger.append(e, key, patch, t)
                if {str(k): int(v_) for k, v_ in additions.items()} != info["by_observed_id"]:
                    raise SystemExit(f"{PREFIX} STOP event {e}: memory additions differ from the patch counts")
                edir = run / SP.event_rel(e)
                edir.mkdir(parents=True, exist_ok=True)
                np.savez_compressed(edir / "memory-patch.npz", **patch)
                summ = ledger.summary()
                rec_e = {"schema": "NS1d-memory-event-v1", "truth": SP.TRUTH_DERIVED, "event": e, "source": r["source"],
                         "ns1c2_step": r["ns1c2_step"], "active_target": t, "world_gaze_deg": r["world_gaze_deg"],
                         "observation_root": r["observation_root"], "input_products": r["products"],
                         "patch": {"path": f"{SP.event_rel(e)}/memory-patch.npz",
                                   "sha256": sha256(edir / "memory-patch.npz"), **info},
                         "additions": {str(k): int(v_) for k, v_ in sorted(additions.items())},
                         "own_target_additions": int(additions.get(t, 0)),
                         "cross_target_additions": {str(k): int(v_) for k, v_ in sorted(additions.items()) if k != t},
                         "coherent_cross_target_additions": {str(k): int(v_) for k, v_ in sorted(additions.items())
                                                             if k != t and k in SP.COHERENT},
                         "non_scheduler_additions": {str(k): int(v_) for k, v_ in sorted(additions.items())
                                                     if k not in SP.COHERENT},
                         "target_subset_equals_accepted_target_patch": subset,
                         "accepted_map_update": {"refused_equal": refused_equal, "map_before": frec["map_before"],
                                                 "map_after": frec["map_after"], "matched": frec.get("matched"),
                                                 "new": frec.get("new"), "patch_id": r["patch_id"]},
                         "memory_after": summ}
                write_json(edir / "event.json", rec_e)
                event_records[e] = rec_e
                return rec_e

            # ---- tables, decisions, states
            def table(mode: str, machine=None) -> list[dict]:
                rows_ = []
                for i in ids:
                    rec = recs[str(i)]
                    if mode == "M1":
                        o = m1_cache[i][1]
                        label = "ACTIONABLE" if o.get("proposal") is not None else "QUIET"
                    else:
                        o = outs[mode][i]
                        label = machine.statuses[i].label
                    prov = "fresh" if i in fresh[mode].get(cur_event["e"], {}) else "cached"
                    rows_.append(K.entity_row(rec, mode, K.revision(mode, rec, ledger), label, o, prov,
                                              K.memory_counts(rec, ledger)))
                return rows_

            def m0_vs_accepted(e: int) -> list[str]:
                """Every fresh M0 probe equals NS1c2's recorded probe for the same entity and revision."""
                mine = set(fresh["M0"].get(e, {}))
                bad = [] if mine == ns1c2_fresh.get(e, set()) else [
                    f"fresh M0 probes {sorted(mine)} != NS1c2's fresh probes {sorted(ns1c2_fresh.get(e, set()))}"]
                for i, rel in fresh["M0"].get(e, {}).items():
                    acc = (ns1c2(f"initial-probe/probes/e{i:05d}.json") if e == 0 else
                           ns1c2(f"steps/step-{e - 1:02d}/update/probes/e{i:05d}.json"))
                    if not acc.exists():
                        bad.append(f"entity {i}: NS1c2 has no fresh probe after event {e}")
                        continue
                    a = read_json(acc)
                    if list(a["revision"]) != K.revision("M0", recs[str(i)], ledger):
                        bad.append(f"entity {i}: revision differs from NS1c2's")
                    d_ = C2.policy_comparison(a["probe"], C2.jsonable(outs["M0"][i]))
                    if d_:
                        bad.append(f"entity {i}: {d_[:2]}")
                return bad

            machines = {}
            for mode in ("M0", "M2"):
                machines[mode] = PH.SceneMachine(ids, budget=budget, vergence=v, focus=f)

            # ======== B11: memory event 0, the initial M0 / M1 / M2 state
            consume_event(0, None)
            init_map = load_npz(C2.resolve(recs[str(SP.CONTINUING)]["map"]["path"], SP.NS1C2_RUN))
            if not C2.maps_equal(init_map, load_npz(ref_path(el["events"][0]["accepted_target_map"]))):
                raise SystemExit(f"{PREFIX} STOP the NS1c2 initial map of 172 is not NS1b's fused map")
            fix0 = {i: int(recs[str(i)]["own_looks"]) for i in ids}
            quiet_at_resume = {}
            for mode in ("M0", "M2"):
                quiet_at_resume[mode] = K.resume_scene(machines[mode], fix0, current=SP.CONTINUING, bout=1, step=0,
                                                       probe=probe_fn(mode), revision=rev_fn(mode))
            for i in ids:
                m1_probe(i)
            pending = {}
            decision_records = {}
            states_written = []
            current = {"id": SP.CONTINUING, "fix": dict(fix0)}

            def decide(k: int) -> dict:
                """The next action of every mode before accepted NS1c2 step k (memory holds events 0..k)."""
                e = k
                plans, acts = {}, {}
                for mode in ("M0", "M2"):
                    mm = machines[mode]
                    plans[mode] = mm.decide(K.refuse_gate)
                    t_ = plans[mode].get("target_id")
                    acts[mode] = K.plan_action(plans[mode], outs[mode].get(t_) if t_ is not None else None)
                m1_probes = {i: m1_cache[i][1] for i in ids}
                acts["M1"], m1_labels = K.stateless_decision(current["id"], ids, m1_probes, current["fix"], budget)
                acc_dec = read_json(ref_path(el["events"][k + 1]["decision"]))
                acc = K.accepted_action(acc_dec)
                diffs = {mode: K.action_differences(acts[mode], acc) for mode in SP.MODES}
                rec_d = {"schema": "NS1d-decision-v1", "truth": SP.TRUTH_DERIVED,
                         "before_ns1c2_step": k, "memory_events": list(range(e + 1)),
                         "accepted": acc, "accepted_record": el["events"][k + 1]["decision"],
                         "actions": acts, "differences": diffs, "m1_statuses": m1_labels,
                         "m0_equals_accepted": not diffs["M0"]}
                decision_records[k] = rec_d
                pending[k] = plans
                write_json(run / f"replay/decisions/before-step-{k:02d}.json", rec_d)
                if diffs["M0"]:
                    raise SystemExit(f"{PREFIX} STOP M0 does not reproduce the accepted NS1c2 step-{k} action "
                                     f"{diffs['M0']} (Outcome 4)")
                return acts["M2"]

            def write_state(e: int, extra: dict | None = None) -> None:
                bad0 = m0_vs_accepted(e)
                if bad0:
                    raise SystemExit(f"{PREFIX} STOP M0 probes differ from NS1c2's after event {e}: {bad0[:3]} "
                                     "(Outcome 4)")
                st = {"schema": "NS1d-replay-state-v1", "truth": SP.TRUTH_DERIVED, "after_event": e,
                      "memory_events": list(range(e + 1)), "current": current["id"],
                      "fixations": {str(k_): v_ for k_, v_ in current["fix"].items()},
                      "memory": ledger.summary(),
                      "tables": {mode: table(mode, machines.get(mode)) for mode in SP.MODES},
                      "fresh_probes": {mode: {str(k_): v_ for k_, v_ in fresh[mode].get(e, {}).items()}
                                       for mode in SP.MODES},
                      "machines": {mode: machines[mode].to_json() for mode in ("M0", "M2")},
                      "events_emitted": {mode: machines[mode].events[:] for mode in ("M0", "M2")},
                      "m0_matches_ns1c2_probes": True,
                      "contexts": {kk: context_part(rec) for kk, rec in recs.items()}, **(extra or {})}
                write_json(run / SP.state_rel(e), C2.jsonable(st))
                states_written.append(SP.state_rel(e))

            write_state(0, {"quiet_at_resume": quiet_at_resume, "event_0": SP.event_rel(0)})

            def consume(k: int) -> None:
                """Accepted NS1c2 step k == memory event k+1: replay, memory, own-look context, commit, tables."""
                e = k + 1
                r = el["events"][e]
                t = int(r["target"])
                prev_map = recs[str(t)]["map"]
                rec_e = consume_event(e, prev_map)
                acc_state = read_json(states[k + 1])
                acc_t = acc_state["entities"][str(t)]
                if acc_t["map"]["sha256"] != sha256(ref_path(r["accepted_target_map"])) or \
                        split_ref(acc_t["map"]["path"])[1] != split_ref(r["accepted_target_map"])[1]:
                    raise SystemExit(f"{PREFIX} STOP step {k}: the accepted state's target map is not the fused map")
                changed = []
                for kk, rec in acc_state["entities"].items():
                    if int(kk) == t:
                        continue
                    if context_part(rec) != context_part(recs[kk]):
                        changed.append(int(kk))
                if changed:
                    raise SystemExit(f"{PREFIX} STOP step {k}: non-target contexts changed in the accepted state "
                                     f"{changed}")
                recs[str(t)] = json.loads(json.dumps(acc_t))
                current["fix"][t] += 1
                current["id"] = t
                cur_event["e"] = e
                committed = {}
                for mode in ("M0", "M2"):
                    n_ev = len(machines[mode].events)
                    outcome = ic.ObservationOutcome(initialized=None, record={
                        "memory_event": e, "fusion": rec_e["accepted_map_update"], "additions": rec_e["additions"]})
                    rec_c = machines[mode].commit(pending[k][mode], outcome, probe_fn(mode), rev_fn(mode))
                    committed[mode] = {"events": machines[mode].events[n_ev:],
                                       "states_after": rec_c["service_states_after"]}
                for i in ids:
                    m1_probe(i)
                if machines["M0"].fixations != current["fix"] or machines["M2"].fixations != current["fix"]:
                    raise SystemExit(f"{PREFIX} STOP the adapter fixations differ from the replayed own looks")
                write_state(e, {"accepted_step": k, "accepted_state": f"run:scene/{states[k + 1].name}",
                                "committed": committed, "event_record": SP.event_rel(e)})

            final_rec = {}

            def final() -> None:
                """After event 8: the memory-enriched post-step-7 state; the M2 / M0 next decision, NOT EXECUTED."""
                for mode in ("M0", "M2"):
                    mm = PH.SceneMachine.from_json(machines[mode].to_json())
                    plan = mm.decide(K.refuse_gate)
                    t_ = plan.get("target_id")
                    final_rec[mode] = {**K.plan_action(plan, outs[mode].get(t_) if t_ is not None else None),
                                       "executed": False, "label": SP.LABEL_NOT_EXECUTED}
                m1_act, m1_labels = K.stateless_decision(current["id"], ids, {i: m1_cache[i][1] for i in ids},
                                                         current["fix"], budget)
                final_rec["M1"] = {**m1_act, "executed": False, "label": SP.LABEL_NOT_EXECUTED}

            result = K.drive(SP.NS1C2_STEPS, decide, lambda k: decision_records[k]["accepted"], consume, final)
            reactivations = []
            for ev_ in machines["M2"].events:
                if ev_["event"] == "natural_reactivation":
                    reactivations.append(C2.jsonable(ev_))
            consumed_events = sorted(event_records)
            if result["divergence"]:
                k = result["step"]
                rec_d = decision_records[k]
                attr = K.attribution(rec_d["actions"]["M1"], rec_d["actions"]["M2"], rec_d["accepted"])
                first_m1 = next((kk for kk in sorted(decision_records)
                                 if decision_records[kk]["differences"]["M1"]), None)
                coherent_cross_before = sum(sum(event_records[e_]["coherent_cross_target_additions"].values())
                                            for e_ in consumed_events)
                div = {"schema": "NS1d-divergence-v1", "truth": SP.TRUTH_DERIVED,
                       "statement": "FIRST CAUSAL DIVERGENCE: the M2 next action differs from the accepted NS1c2 action; "
                                    "the replay stops here and no later observation is consumed",
                       "before_ns1c2_step": k, "after_memory_event": k, "differences": result["differences"],
                       "accepted_action": rec_d["accepted"], "m0_action": rec_d["actions"]["M0"],
                       "m1_action": rec_d["actions"]["M1"], "m2_action": rec_d["actions"]["M2"],
                       "attribution": attr, "first_m1_divergence_before_step": first_m1,
                       "coherent_cross_target_points_in_memory": coherent_cross_before,
                       "consumed_events": consumed_events, "next_observation_consumed": False,
                       "m2_divergent_action": {**rec_d["actions"]["M2"], "executed": False,
                                               "label": SP.LABEL_NOT_EXECUTED}}
                write_json(run / "replay/divergence.json", C2.jsonable(div))
                reading = attr["reading"]
            else:
                div = None
                first_m1 = next((kk for kk in sorted(decision_records)
                                 if decision_records[kk]["differences"]["M1"]), None)
                reading = "Outcome 2 - memory bridge works, no action divergence through step 7"
                write_json(run / "replay/final.json", C2.jsonable({
                    "schema": "NS1d-final-v1", "truth": SP.TRUTH_DERIVED,
                    "statement": "NO ACTION DIVERGENCE THROUGH STEP 7: the memory-enriched post-step-7 state is frozen; "
                                 "the next decisions below are descriptive and NOT EXECUTED",
                    "next_decisions": final_rec, "first_m1_divergence_before_step": first_m1,
                    "consumed_events": consumed_events}))
            # ---- persistent maps: every entity's map is its accepted one (untouched ones unchanged since the start)
            last = read_json(states[len(consumed_events) - 1])
            map_check = {kk: rec["map"]["sha256"] == last["entities"][kk]["map"]["sha256"] for kk, rec in recs.items()}
            untouched = {kk: recs[kk]["map"]["sha256"] == st0["entities"][kk]["map"]["sha256"] for kk in recs
                         if all(int(r_["target"]) != int(kk) for r_ in el["events"][1:len(consumed_events)])}
            out = {"schema": "NS1d-replay-v1", "truth": SP.TRUTH_DERIVED, "code": cs,
                   "statement": "the accepted instance-keyed measurement memory over the controller-phase observations; "
                                "M0 / M1 / M2 read-only; the replay stops at the first M2 action divergence",
                   "consumed_events": consumed_events, "decisions": sorted(decision_records),
                   "divergence": div is not None, "divergence_record": "replay/divergence.json" if div else None,
                   "final_record": None if div else "replay/final.json", "outcome_reading": reading,
                   "first_m1_divergence_before_step": first_m1, "natural_reactivations": reactivations,
                   "memory": ledger.summary(), "states": states_written,
                   "maps_equal_accepted_state": map_check, "untouched_maps_unchanged": untouched,
                   "quiet_at_resume": quiet_at_resume, "gate_guard": gg.record(),
                   "probe_calls": {mode: machines[mode].calls for mode in ("M0", "M2")},
                   "probe_cache_hits": {mode: machines[mode].hits for mode in ("M0", "M2")}}
            if not all(map_check.values()) or not all(untouched.values()):
                failure = "a persistent map differs from the accepted one"
            write_json(run / "replay/replay.json", C2.jsonable(out))
            files = sorted(str(p.relative_to(run)) for p in (run / "replay").rglob("*") if p.is_file()
                           and p.name != "replay-opened-files.json")
            write_json(run / "freeze/replay-freeze.json", {
                "schema": "NS1d-replay-freeze-v1", "truth": SP.TRUTH_DERIVED, "frozen_utc": utc(), "code": cs,
                "statement": "the replay products frozen at the stop (first divergence or end of the accepted trace)",
                "files": {f_: sha256(run / f_) for f_ in files}})
    finally:
        write_json(run / "replay/replay-opened-files.json", guard_record(g, pg))
    if failure:
        raise SystemExit(f"{PREFIX} STOP {failure} (Outcome 4)")
    return {"consumed_events": out["consumed_events"], "divergence": out["divergence"],
            "reading": out["outcome_reading"], "reactivations": len(out["natural_reactivations"])}


# ------------------------------------------------------------------ visuals and manifest
def visualize(ctx: Ctx, vis: Path) -> dict:
    run = ctx.run
    need(run / "replay/replay.json", "replay")
    import ns1d_visuals as V
    man = V.visualize(run, vis)
    write_manifest(run)
    return {k: v["sha256"] for k, v in man["figures"].items()}


def write_manifest(run: Path) -> dict:
    files = sorted(str(p.relative_to(run)) for p in run.rglob("*") if p.is_file()
                   and p.name not in ("manifest.json", "check-summary.json", "process-log.jsonl"))
    m = {"schema": "NS1d-manifest-v1", "experiment": SP.EXPERIMENT, "contract": SP.CONTRACT, "code": code_state(),
         "base_commit": SP.BASE_COMMIT, "truth": TRUTH_CLASSES, "files": {f: sha256(run / f) for f in files}}
    write_json(run / "manifest.json", m)
    return m


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=SP.COMMANDS)
    ap.add_argument("--run", type=Path, default=SP.RUN_DEFAULT)
    ap.add_argument("--visuals", type=Path, default=None)
    ap.add_argument("--dev", action="store_true", help="scratch development run only (never the canonical RUN)")
    a = ap.parse_args(argv)
    ctx = Ctx(a.run, a.dev)
    t0 = time.time()
    fns = {"source": source, "synthetic": synthetic, "known-answer": known_answer, "events": events,
           "replay": replay, "visualize": lambda c: visualize(c, a.visuals or SP.VIS_DEFAULT)}
    try:
        out = fns[a.command](ctx)
    except Refused as e:
        log_process(ctx, a.command, t0, "refused", {"error": str(e.code)})
        raise
    except SystemExit as e:
        if e.code not in (0, None):
            log_process(ctx, a.command, t0, "failed", {"error": str(e.code)})
        raise
    except BaseException as e:
        log_process(ctx, a.command, t0, "failed", {"error": repr(e)})
        raise
    log_process(ctx, a.command, t0, "ok", {"result": out})
    print(f"{PREFIX} {a.command} ok " + json.dumps(out, sort_keys=True, default=str)[:800], flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
