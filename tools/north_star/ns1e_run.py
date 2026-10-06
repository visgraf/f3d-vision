"""North Star-1e: the full coherent multi-entity loop with M2 memory (run order, truth boundary, process contract).

Contract: docs/north-star/ns1e-coherent-full-loop-m2-memory-contract.md.

    .venv/bin/python tools/north_star/ns1e_run.py source          --run RUN
    .venv/bin/python tools/north_star/ns1e_run.py synthetic       --run RUN
    .venv/bin/python tools/north_star/ns1e_run.py handoff         --run RUN    # start state + next decision + cap
    .venv/bin/python tools/north_star/ns1e_run.py gate-harness    --run RUN    # M2 / fixed-H0 residue-gate wiring
    .venv/bin/python tools/north_star/ns1e_run.py loop            --run RUN    # steps 8.. to the terminal / cap
    .venv/bin/python tools/north_star/ns1e_run.py freeze-control  --run RUN    # (called by loop at the terminal)
    .venv/bin/python tools/north_star/ns1e_run.py evaluate        --run RUN    # post-control, separate process
    .venv/bin/python tools/north_star/ns1e_run.py visualize       --run RUN --visuals VIS

    step stages (normally launched by ``loop``), each once per global step k:
        schedule | preflight | acquire | freeze-observation | perfect-correspondence | freeze-correspondence |
        spherical-geometry | freeze-geometry | local-oracle-segmentation | freeze-identity | fuse | memory | update
                                                                                          --run RUN --step k

Every canonical stage runs once, from a clean pushed commit, under the accepted ``nb1a_guard.OpenGuard`` allowlist; every
host stage under the accepted ``NoProcessGuard`` (no process, hence no Blender); wherever policy code runs, under the
accepted NS1c2 gate guard (``final_look_gate_v1`` refused outside RESIDUE).  ``--dev`` runs on a scratch development run
(never the canonical RUN); ``loop --dev --rehearsal-spp N`` renders the factory-startup rehearsal room instead of
Classroom; ``--max-steps`` stops a development loop early.
"""
from __future__ import annotations

import argparse
import datetime as dt
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
for _p in (HERE, HERE.parent, HERE.parent / "active_bootstrap", HERE.parent / "natural_bootstrap",
           HERE.parent / "classroom_oracle", REPO):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import ns1e_spec as SP  # noqa: E402
from nb1a_guard import OpenGuard  # noqa: E402  (accepted, read-only)

PREFIX = "[ns1e]"
TRUTH_CLASSES = {
    "ORACLE INPUT": "the new rendered observations; the ORACLE AID (Position, Object Index) used by the PERFECT "
                    "correspondence service, the local segmentation aid and the inherited controller-time oracle "
                    "matcher of the target's own look",
    "DERIVED": "the start-state reconstruction, the M2 probes, the Controller-02 statuses, dispositions, phases and "
               "scheduler decisions, the world-gaze mappings, the truth-stripped correspondences, the spherical geometry, "
               "the local identity attachment, the H0 fusions, the memory events and the scene checkpoints",
    "ACCEPTED HISTORICAL REFERENCE": "the frozen NS1c2 / NS1d records the start state is reconstructed from, and "
                                     "Controller-01's 98.34 % (context only, not numerically comparable)",
    "REFERENCE / EVALUATION": "the accepted Breadth-1 0.5-degree reference, opened only by `evaluate` after the control "
                              "freeze; the sealed instance catalogs (never opened)",
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


def read_members(path: Path, keys) -> dict:
    with np.load(path, allow_pickle=False) as z:
        return {k: np.asarray(z[k]) for k in keys}


def arrays_equal(a: dict, b: dict) -> bool:
    return set(a) == set(b) and all(np.asarray(a[k]).dtype == np.asarray(b[k]).dtype
                                    and np.array_equal(np.asarray(a[k]), np.asarray(b[k])) for k in a)


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
    def __init__(self, run: Path, dev: bool, step: int | None = None, rehearsal_spp: int | None = None) -> None:
        self.run, self.dev, self.step, self.rehearsal_spp = run.resolve(), dev, step, rehearsal_spp
        if dev and self.run == SP.RUN_DEFAULT.resolve():
            raise SystemExit(f"{PREFIX} STOP --dev never runs on the canonical RUN")
        if rehearsal_spp is not None and not dev:
            raise SystemExit(f"{PREFIX} STOP --rehearsal-spp is a development rehearsal option only")

    def sd(self) -> Path:
        if self.step is None:
            raise SystemExit(f"{PREFIX} STOP a step stage needs --step")
        return self.run / SP.step_dir(self.step)


def log_process(ctx: Ctx, command: str, t0: float, status: str, extra: dict | None = None) -> None:
    ctx.run.mkdir(parents=True, exist_ok=True)
    entry = {"command": command, "step": ctx.step, "argv": sys.argv, "executable": sys.executable,
             "code": code_state(), "dev": ctx.dev, "started_utc": dt.datetime.fromtimestamp(
                 t0, dt.timezone.utc).isoformat(timespec="seconds"), "finished_utc": utc(),
             "seconds": round(time.time() - t0, 3), "status": status, **(extra or {})}
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


def no_process(light: bool = False):
    """The accepted NoProcessGuard (policy stages), or the NS1e guard with the same audit events (measurement, fusion
    and memory stages, which must not load the controller stack the accepted guard's module imports)."""
    if light:
        import ns1e_core as CORE
        return CORE.ProcessGuard()
    from fov3d.experiments.classroom_oracle.controller02 import NoProcessGuard   # accepted, unchanged
    return NoProcessGuard()


def process_record(pg) -> dict | None:
    if pg is None or not hasattr(pg, "attempts"):
        return None
    name = f"{type(pg).__module__}.{type(pg).__name__}"
    return {"guard": name, "events": list(pg.EVENTS), "attempts": list(pg.attempts)}


def guard_record(g: OpenGuard, pg=None, extra: dict | None = None) -> dict:
    rec = g.record()
    rec["modules_loaded"] = {m: m in sys.modules for m in ("cv2", "fsg_stereo", "ab1a_stereo", "ab1d_match",
                                                           "ab1d3_sgbm", "ab1b_oracle", "fsg6f_frontier",
                                                           "fov3d.control.integrated", "fov3d.control.controller02")}
    rec["violations_count"] = len(rec["violations"])
    rec["forbidden_reads"] = sorted({e["path"] for e in rec["events"] if e.get("event") == "open" and forbidden(e["path"])})
    rec["process_guard"] = process_record(pg)
    rec.update(extra or {})
    return rec


def verify_record_hashes(base: Path, freeze_rel: str) -> dict:
    fz = read_json(base / freeze_rel)
    bad = {f: h for f, h in fz["files"].items() if sha256(base / f) != h}
    if bad:
        raise SystemExit(f"{PREFIX} STOP files changed after {freeze_rel}: {sorted(bad)[:5]}")
    return fz


def freeze_reads(base: Path, freezes) -> list[Path]:
    """Every file a set of freeze records lists (read before a guard, so that a stage may re-verify them)."""
    out = []
    for fz in freezes:
        out.append(base / fz)
        if (base / fz).is_file():
            out += [base / f for f in read_json(base / fz)["files"]]
    return out


def head_pose(c: dict) -> tuple[np.ndarray, np.ndarray]:
    return np.asarray(c["head_R_wh"], np.float64), np.asarray(c["head_origin_w_m"], np.float64)


def res(ref: str, run: Path) -> Path:
    import ns1e_core as CORE
    return CORE.resolve(ref, run)


def manifest_of(run_dir: Path, pin: str) -> dict:
    if sha256(run_dir / "manifest.json") != pin:
        raise SystemExit(f"{PREFIX} STOP the manifest of {run_dir} is not the pinned one")
    return read_json(run_dir / "manifest.json")


def verify_in_manifest(run_dir: Path, man: dict, rels) -> dict:
    out, bad = {}, []
    for rel in rels:
        h = sha256(run_dir / rel)
        if man["files"].get(rel) != h:
            bad.append(rel)
        out[rel] = h
    if bad:
        raise SystemExit(f"{PREFIX} STOP files of {run_dir.name} differ from their pinned manifest: {bad[:5]}")
    return out


def record_reads(recs: dict, run: Path) -> list[Path]:
    import ns1e_core as CORE
    out = []
    for rec in recs.values():
        out += [CORE.resolve(r, run) for r in CORE.record_refs(rec)]
    return sorted(set(out))


def memory_reads(events: list[dict], run: Path) -> list[Path]:
    return [res(e["patch"], run) for e in events]


def state_file(path: Path, st: dict, valid: np.ndarray) -> None:
    np.savez_compressed(path, ids_left=st["ids_left"], ids_right=st["ids_right"], raw_support_L=st["raw_support_L"],
                        raw_support_R=st["raw_support_R"], matcher_valid=np.asarray(valid, bool))


def probe_file_record(entity: int, computed_at: str, revision, out: dict, counts: dict, extra: dict | None = None) -> dict:
    import ns1e_core as CORE
    return {"schema": "NS1e-probe-v1", "truth": SP.TRUTH_DERIVED, "entity": int(entity), "computed_at": computed_at,
            "mode": "M2", "revision": list(revision), "phase_at_probe": "NORMAL", "gate_called": False,
            "memory": counts, "probe": CORE.jsonable(out), **(extra or {})}


def with_status(rec: dict, st, probe_out: dict | None = None) -> dict:
    import ns1c2_core as C2
    rec = dict(rec)
    rec["status"] = C2.status_record(st)
    if probe_out is not None:
        rec["proposal"] = C2.proposal_summary(probe_out)
        rec["policy"] = C2.policy_summary(probe_out)
    return rec


def scene_table(ents: dict) -> list[dict]:
    rows = []
    for k in sorted(ents, key=int):
        e = ents[k]
        rows.append({"temporary_entity_id": int(k), "own_looks": e["own_looks"], "map_surfels": e["map"]["surfels"],
                     "revision": e["revision"], "label": e["status"]["label"], "local_state": e["status"]["local"],
                     "disposition": e["status"]["disposition"], "reason": e["status"]["reason"],
                     "proposal": e.get("proposal"), "memory": e.get("memory"),
                     "fsg6f": ((e.get("policy") or {}).get("fsg6f") or {}).get("reason"),
                     "cyclopean": ((e.get("policy") or {}).get("cyclopean") or {}).get("reason"),
                     "probe_provenance": (e.get("probe") or {}).get("provenance")})
    return rows


def plan_to_json(plan: dict) -> dict:
    import ns1c2_phase as PH
    a = plan.get("action")
    return {**{k: v for k, v in plan.items() if k not in ("action", "before")},
            "action": None if a is None else {"target_id": int(a.target_id), "gaze_deg": list(a.gaze_yaw_pitch_deg),
                                              "source": a.source},
            "before": None if plan.get("before") is None else PH.status_to_json(plan["before"])}


def plan_from_json(p: dict):
    import ns1c2_core as C2
    import ns1c2_phase as PH
    from fov3d.control import integrated as ic
    v, f = C2.vergence_focus()
    a = p["action"]
    return {**p, "action": ic.Observe(int(a["target_id"]), tuple(a["gaze_deg"]), v, f, a["source"]),
            "before": PH.status_from_json(p["before"])}


def ledger_from(state: dict, run: Path, extra_events: list[dict] | None = None):
    """The accepted ledger, rebuilt read-only from every frozen memory event of a checkpoint (and optional new ones)."""
    import ns1e_core as CORE
    events = list(state["memory"]["events"]) + list(extra_events or [])
    ledger = CORE.rebuild_ledger(events, run)
    return ledger, events


def require_memory_digest(ledger, want: str, what: str) -> dict:
    import ns1e_core as CORE
    summ = ledger.summary()
    if CORE.ledger_digest(summ) != want:
        raise SystemExit(f"{PREFIX} STOP the rebuilt memory differs from {what} (duplicate, missing or altered event)")
    return summ


def accepted_constants() -> dict:
    """The accepted policy / fusion / budget constants (the NS1c2 check, reused)."""
    import ns1c2_run
    return ns1c2_run.accepted_constants()


# ------------------------------------------------------------------ source
def ns1d_accepted_on_base() -> dict:
    t = git("show", f"{SP.BASE_COMMIT}:{SP.NS1D_REPORT}")
    return {"marker": SP.NS1D_ACCEPTED_MARKER in t, "status": "**Status: ACCEPTED.**" in t}


def ns1c_not_accepted() -> dict:
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
           for name, sha in (("base", SP.BASE_COMMIT), ("ns1d_acceptance", SP.NS1D_ACCEPTANCE),
                             ("ns1c2_acceptance", SP.NS1C2_ACCEPTANCE), ("contract", SP.CONTRACT_COMMIT))}
    contract_unchanged = subprocess.run(["git", "diff", "--quiet", SP.CONTRACT_COMMIT, "--", SP.CONTRACT],
                                        cwd=REPO).returncode == 0
    ns1d = ns1d_accepted_on_base()
    ns1c = ns1c_not_accepted()
    if (SP.CANONICAL_REMOTE not in origin or "fov-3d-vision" in origin or not all(anc.values())
            or not contract_unchanged or not all(ns1d.values()) or not ns1c["ok"]):
        raise SystemExit(f"{PREFIX} STOP provenance: origin {origin}; ancestors {anc}; contract unchanged "
                         f"{contract_unchanged}; NS1d accepted {ns1d}; NS1c {ns1c}")
    import ns1b_chart as CH
    CH.ensure_policy_modules()
    reads = ([SP.NS1A_RUN / f for f in SP.NS1A_PINS] + [SP.NS1C2_RUN / "manifest.json"]
             + [SP.NS1C2_RUN / f for f in SP.NS1C2_PINS] + [SP.NS1D_RUN / "manifest.json"]
             + [SP.NS1D_RUN / f for f in SP.NS1D_PINS])
    (run / "source").mkdir(parents=True, exist_ok=True)
    g = OpenGuard("ns1e-source", reads, [run / "source"])
    pg = no_process()
    try:
        with g, pg:
            pins = {p: sha256(REPO / p) for p in SP.SOURCE_PINS}
            bad = {p: h for p, h in pins.items() if h != SP.SOURCE_PINS[p]}
            if bad:
                raise SystemExit(f"{PREFIX} STOP accepted sources changed: {bad}")
            a_pins = {rel: sha256(SP.NS1A_RUN / rel) for rel in SP.NS1A_PINS}
            if a_pins != SP.NS1A_PINS:
                raise SystemExit(f"{PREFIX} STOP the frozen NS1a seed handoff changed")
            m_c2 = manifest_of(SP.NS1C2_RUN, SP.NS1C2_MANIFEST_SHA256)
            c2_pins = verify_in_manifest(SP.NS1C2_RUN, m_c2, list(SP.NS1C2_PINS))
            m_d = manifest_of(SP.NS1D_RUN, SP.NS1D_MANIFEST_SHA256)
            d_pins = {rel: sha256(SP.NS1D_RUN / rel) for rel in SP.NS1D_PINS}
            in_man = {rel: m_d["files"].get(rel) == h for rel, h in d_pins.items() if rel != "check-summary.json"}
            if c2_pins != SP.NS1C2_PINS or d_pins != SP.NS1D_PINS or not all(in_man.values()):
                raise SystemExit(f"{PREFIX} STOP the frozen NS1c2 / NS1d inputs changed: {c2_pins} {d_pins} {in_man}")
            summ = read_json(SP.NS1D_RUN / "check-summary.json")
            if summ.get("marker") != "NORTH_STAR1D_CHECKS_PASS" or summ.get("failed"):
                raise SystemExit(f"{PREFIX} STOP the NS1d check summary does not pass")
            consts = accepted_constants()
            out = {"schema": "NS1e-source-v1", "experiment": SP.EXPERIMENT, "code": cs, "origin": origin,
                   "ancestors": anc, "contract": SP.CONTRACT, "contract_commit": SP.CONTRACT_COMMIT,
                   "contract_unchanged": contract_unchanged, "base_commit": SP.BASE_COMMIT,
                   "ns1d_acceptance": SP.NS1D_ACCEPTANCE, "ns1d_accepted_on_base": ns1d, "ns1c_decision": ns1c,
                   "source_pins": pins, "accepted_constants": consts, "ordinary_budget": consts["ORDINARY_BUDGET"],
                   "ns1a_pins": a_pins, "ns1c2_manifest": SP.NS1C2_MANIFEST_SHA256, "ns1c2_pins": c2_pins,
                   "ns1d_manifest": SP.NS1D_MANIFEST_SHA256, "ns1d_pins": d_pins, "ns1d_check_marker": summ["marker"],
                   "breadth1_reference_pin": {"path": f"{SP.B1_RUN}/{SP.B1_EXR}", "sha256": SP.B1_EXR_SHA256,
                                              "opened": False, "statement": "pinned only; opened by `evaluate` after the "
                                                                           "control freeze"},
                   "scene_machine": "tools/north_star/ns1c2_phase.SceneMachine (accepted, unchanged)",
                   "scheduler": "fov3d.control.controller02.schedule_normal (accepted, unchanged)",
                   "memory": "fov3d.reconstruction.measurement_memory (accepted, unchanged) through ns1d_core.MemoryLedger"}
            write_json(run / "source/source-manifest.json", out)
    finally:
        write_json(run / "source/source-opened-files.json", guard_record(g, pg))
    return {"pins": len(pins), "budget": consts["ORDINARY_BUDGET"], "ns1d_accepted": all(ns1d.values())}


# ------------------------------------------------------------------ synthetic known answers
def synthetic(ctx: Ctx) -> dict:
    run = ctx.run
    need(run / "source/source-manifest.json", "source")
    once(run / "synthetic/synthetic-report.json", "the synthetic known answers")
    require_committed(ctx, "synthetic")
    import ns1e_synthetic as SY
    rep = SY.run_all()
    write_json(run / "synthetic/synthetic-report.json", rep)
    if rep["failed"]:
        raise SystemExit(f"{PREFIX} STOP synthetic known answers failed: {rep['failed']}")
    return {"passed": rep["count"] - len(rep["failed"]), "count": rep["count"], "marker": rep["marker"]}


# ------------------------------------------------------------------ handoff: the exact start state (contract section 6)
def ns1d_event_rows() -> tuple[list[dict], list[Path]]:
    """The nine NS1d memory events as NS1e ledger rows (patch, hash, key, target, additions), from the frozen records."""
    el = read_json(SP.NS1D_RUN / "events/event-list.json")
    rows, paths = [], []
    for r in el["events"]:
        e = int(r["event"])
        er = read_json(SP.NS1D_RUN / f"replay/events/event-{e:02d}/event.json")
        rows.append({"event": e, "source": "ns1d", "global_step": None if r["ns1c2_step"] is None else int(r["ns1c2_step"]),
                     "origin": r["source"], "target": int(r["target"]), "observation_key": r["observation_freeze_sha256"],
                     "patch": f"ns1d:{er['patch']['path']}", "patch_sha256": er["patch"]["sha256"],
                     "additions": {str(k): int(v) for k, v in er["additions"].items()}})
        paths.append(SP.NS1D_RUN / f"replay/events/event-{e:02d}/event.json")
    return rows, paths


def planar_source(rec: dict) -> tuple[str, str]:
    """Where the accepted NS1c2 records hold the planar controller-state target support of an entity's LAST own look."""
    ref = rec["looks"][-1]["state"]
    scheme, rel = ref.split(":", 1)
    if scheme == "run" and rel.startswith("steps/") and rel.endswith("/update/controller-state.npz"):
        return rel.replace("controller-state.npz", "update.json"), "controller_state_target_support"
    if scheme == "run" and rel.startswith("contexts/looks/ns1b-action/"):
        return "contexts/contexts.json", "ns1b_action_look"
    if scheme == "run" and rel.startswith("contexts/looks/rank-"):
        return "contexts/contexts.json", "controller_state_target_support"
    raise SystemExit(f"{PREFIX} STOP no recorded planar support for the last look {ref}")


def handoff(ctx: Ctx) -> dict:
    run = ctx.run
    need(run / "synthetic/synthetic-report.json", "synthetic")
    if read_json(run / "synthetic/synthetic-report.json").get("failed") != []:
        raise Refused(f"{PREFIX} REFUSED the synthetic known answers must pass first")
    once(run / "handoff/handoff.json", "the handoff")
    cs = require_committed(ctx, "handoff")
    import ns1b_chart as CH
    import ns1b_core as B
    import ns1c2_core as C2
    import ns1c2_phase as PH
    import ns1d_core as K
    import ns1e_core as CORE
    from fov3d.control import controller02 as c2
    CH.ensure_policy_modules()
    import ns1a_core  # noqa: F401
    import fsg6f_frontier  # noqa: F401
    st7 = read_json(SP.NS1C2_RUN / "scene/state-after-step-07.json")
    recs_c2 = {k: v for k, v in st7["entities"].items()}
    ev_rows, ev_paths = ns1d_event_rows()
    planar_src = {k: planar_source(rec) for k, rec in recs_c2.items()}
    reads = ([SP.NS1A_RUN / f for f in SP.NS1A_PINS] + [SP.NS1C2_RUN / "manifest.json", SP.NS1D_RUN / "manifest.json"]
             + [SP.NS1C2_RUN / f for f in SP.NS1C2_PINS] + [SP.NS1D_RUN / f for f in SP.NS1D_PINS] + ev_paths
             + [SP.NS1D_RUN / r["patch"].split(":", 1)[1] for r in ev_rows]
             + [C2.resolve(r, SP.NS1C2_RUN) for rec in recs_c2.values() for r in CORE.record_refs(
                 {k: v for k, v in rec.items() if k != "probe"})]
             + [SP.NS1C2_RUN / s for s, _key in planar_src.values() if s])
    for sub in ("handoff/probes", "scene", "freeze"):
        (run / sub).mkdir(parents=True, exist_ok=True)
    g = OpenGuard("ns1e-handoff", reads, [run / "handoff", run / "scene", run / "freeze"])
    pg = no_process()
    problems: list[str] = []
    out = None
    try:
        with g, pg, PH.GateGuard(c2.ScenePhase.NORMAL.value, "ns1e handoff") as gg:
            # -- pins and manifests (every NS1c2 / NS1d file consumed equals its manifest entry)
            m_c2 = manifest_of(SP.NS1C2_RUN, SP.NS1C2_MANIFEST_SHA256)
            m_d = manifest_of(SP.NS1D_RUN, SP.NS1D_MANIFEST_SHA256)
            verify_in_manifest(SP.NS1C2_RUN, m_c2, list(SP.NS1C2_PINS))
            verify_in_manifest(SP.NS1D_RUN, m_d, [f for f in SP.NS1D_PINS if f != "check-summary.json"]
                               + [str(p.relative_to(SP.NS1D_RUN)) for p in ev_paths]
                               + [r["patch"].split(":", 1)[1] for r in ev_rows])
            for rel, h in {**{f"ns1a:{k}": v for k, v in SP.NS1A_PINS.items()},
                           **{f"ns1c2:{k}": v for k, v in SP.NS1C2_PINS.items()},
                           **{f"ns1d:{k}": v for k, v in SP.NS1D_PINS.items()}}.items():
                if sha256(CORE.resolve(rel, run)) != h:
                    problems.append(f"pin {rel}")
            c2_rels = sorted({r.split(":", 1)[1] for rec in recs_c2.values() for r in CORE.record_refs(
                {k: v for k, v in rec.items() if k != "probe"}) if r.startswith("run:")})
            verify_in_manifest(SP.NS1C2_RUN, m_c2, c2_rels)
            for k, rec in recs_c2.items():
                for look in rec["looks"]:
                    for key, hk in (("calibration", "calibration_sha256"), ("state", "state_sha256")):
                        if sha256(C2.resolve(look[key], SP.NS1C2_RUN)) != look[hk]:
                            problems.append(f"entity {k}: look {key} hash")
                for key in ("evidence", "map"):
                    if sha256(C2.resolve(rec[key]["path"], SP.NS1C2_RUN)) != rec[key]["sha256"]:
                        problems.append(f"entity {k}: {key} hash")
            fin = read_json(SP.NS1C2_RUN / "scene/final-scene-state.json")
            if {k: v for k, v in fin.items() if k != "label"} != {k: v for k, v in st7.items() if k != "label"}:
                problems.append("NS1c2 final-scene-state != state-after-step-07")
            verify_in_manifest(SP.NS1C2_RUN, m_c2, sorted({s for s, _key in planar_src.values() if s}))
            diag = read_json(SP.NS1C2_RUN / "contexts/contexts.json")["diagnostics"]
            planar = {}
            for k, (src, key) in planar_src.items():
                if src == "contexts/contexts.json":
                    planar[k] = int(diag[k][key] if key == "controller_state_target_support"
                                    else diag[k]["ns1b_action_look"]["controller_state_target_support"])
                else:
                    planar[k] = int(read_json(SP.NS1C2_RUN / src)["controller_state_target_support"])
            # -- eligibility (re-derived) and charts (recomputed at the ORIGINAL NS1a gaze)
            el = C2.derive_coherent_set(read_json(SP.NS1A_RUN / "seeds/seed-set.json"))
            gazes = B.rank_gazes(read_json(SP.NS1A_RUN / "source/nb1c-gaze-list.json"))
            ids = el["coherent_ids"]
            elig = {"schema": "NS1e-eligibility-v1", "truth": SP.TRUTH_DERIVED, "rule": el["rule"],
                    "fields_read": el["fields_read"], "coherent_ids": ids, "ambiguous_ids": el["deferred_ids"],
                    "outside_ids": el["outside_ids"], "expected_coherent": list(SP.EXPECTED_COHERENT),
                    "expected_ambiguous": list(SP.EXPECTED_AMBIGUOUS),
                    "matches_expectation": ids == list(SP.EXPECTED_COHERENT)
                    and el["deferred_ids"] == list(SP.EXPECTED_AMBIGUOUS),
                    "ambiguous_state": SP.AMBIGUOUS_STATE, "statement": "the scheduler universe is re-derived from the "
                    "frozen NS1a seed set by the accepted single-patch rule; no name, catalog or visibility"}
            if not elig["matches_expectation"]:
                problems.append(f"eligibility {ids} / {el['deferred_ids']} differs from the expectation (STOP)")
            write_json(run / "handoff/eligibility.json", elig)
            c2_charts = read_json(SP.NS1C2_RUN / "charts/policy-charts.json")["charts"]
            charts = {}
            for row in el["coherent"]:
                k = int(row["temporary_entity_id"])
                ch = C2.chart_record(k, row["initialized_at_rank"], tuple(gazes[int(row["initialized_at_rank"])]))
                same = np.array_equal(np.asarray(ch["R_HC"]), np.asarray(c2_charts[str(k)]["R_HC"])) and \
                    ch["R_HC_sha256"] == c2_charts[str(k)]["R_HC_sha256"]
                if not ch["checks"]["ok"] or not same:
                    problems.append(f"chart {k}: checks {ch['checks']['ok']}, equals NS1c2 {same}")
                charts[str(k)] = {**ch, "equals_ns1c2_chart": bool(same)}
            write_json(run / "handoff/charts.json", {"schema": "NS1e-charts-v1", "truth": SP.TRUTH_DERIVED,
                                                     "label": SP.LABEL_CHART, "charts": charts,
                                                     "statement": "one FIXED chart per coherent entity, recomputed at "
                                                                  "its ORIGINAL NS1a initialization gaze; never "
                                                                  "recentered; NOT physical head motion"})
            # -- records (re-scoped) and their contexts against the accepted function and NS1d's contexts
            s8 = read_json(SP.NS1D_RUN / "replay/state-after-event-08.json")
            recs = {k: CORE.rescope(v) for k, v in recs_c2.items()}
            if sorted(int(k) for k in recs) != ids:
                problems.append("the NS1c2 entity set is not the coherent set")
            ctx_eq = {}
            for k in sorted(recs, key=int):
                part_d = CORE.rescope({**s8["contexts"][k], "looks": s8["contexts"][k]["looks"]})
                part_e = {f: recs[k][f] for f in s8["contexts"][k]}
                if CORE.jsonable(part_e) != CORE.jsonable(part_d):
                    problems.append(f"entity {k}: context differs from NS1d's after event 8")
                a = CORE.context_from_record(recs[k], run)
                b = C2.context_from_record(recs_c2[k], SP.NS1C2_RUN)
                d = CORE.contexts_equal(a, b)
                ctx_eq[k] = {"equal_to_accepted_function": not d, "differences": d}
                if d:
                    problems.append(f"entity {k}: the NS1e context differs from the accepted function: {d}")
            # -- the memory ledger (nine frozen NS1d patches)
            ledger = CORE.rebuild_ledger(ev_rows, run)
            summ = ledger.summary()
            mem_equal = CORE.jsonable(summ) == CORE.jsonable(s8["memory"])
            if not mem_equal:
                problems.append("the rebuilt memory differs from NS1d's after event 8")
            # -- fresh M2 probes against the frozen NS1d M2 machine cache
            md = s8["machines"]["M2"]
            budget = C2.budget_live()
            v, f = C2.vergence_focus()
            outs, written, probe_eq = {}, {}, {}
            for k in sorted(recs, key=int):
                i = int(k)
                rev = CORE.revision_m2(recs[k], ledger)
                o = CORE.probe_m2(recs[k], charts[k], run, ledger, f"handoff M2 probe entity {i}")
                pth = run / f"handoff/probes/e{i:05d}.json"
                write_json(pth, probe_file_record(i, "handoff", rev, o, CORE.memory_counts(recs[k], ledger)))
                outs[i] = o
                written[i] = {"path": f"run:handoff/probes/e{i:05d}.json", "sha256": sha256(pth), "revision": rev,
                              "provenance": "fresh", "computed_at": "handoff"}
                cached = md["cache"][k]
                eq_pol = CORE.probe_policy_part(o) == CORE.cached_policy_part(cached["probe"])
                eq_rev = list(cached["revision"]) == rev
                probe_eq[k] = {"policy_equal": eq_pol, "revision_equal": eq_rev, "revision": rev,
                               "p3_calls": o["adapter"]["calls"]["P3"]}
                if not (eq_pol and eq_rev) or o["adapter"]["calls"]["P3"]:
                    problems.append(f"entity {i}: the fresh M2 probe differs from NS1d's cached probe ({probe_eq[k]})")
            # -- the machine: the accepted NS1d resume semantics, compared with the frozen NS1d M2 machine
            quiet_frozen = {int(a): b for a, b in md["quiet_since"].items()}
            if len(set(quiet_frozen.values())) > 1:
                problems.append("more than one quiet_since value at the resume point (not expected)")
            qs = next(iter(quiet_frozen.values())) if quiet_frozen else None
            m = PH.SceneMachine(ids, budget=budget, vergence=v, focus=f)
            quiet = K.resume_scene(m, {i: int(recs[str(i)]["own_looks"]) for i in ids}, current=int(md["current"]),
                                   bout=int(md["bout"]), step=int(md["step"]),
                                   probe=lambda i: C2.probe_result(outs[i], i, {"probe_path": written[i]["path"],
                                                                                "revision": written[i]["revision"]}),
                                   revision=lambda i: CORE.revision_m2(recs[str(i)], ledger), quiet_since=qs)
            mj = m.to_json()
            fields = ("order", "budget", "disposition", "fixations", "statuses", "recorded", "phase", "current", "bout",
                      "step", "quiet_since", "reactivated_since_attended", "terminal", "phases", "residue_decisions",
                      "final_observed", "final_rejected", "gate_log")
            machine_eq = {fl: CORE.jsonable(mj[fl]) == CORE.jsonable(md[fl]) for fl in fields}
            machine_eq["initialized"] = sorted(mj["initialized"]) == sorted(md["initialized"])
            machine_eq["cache_revisions"] = {k: list(x["revision"]) for k, x in mj["cache"].items()} == \
                {k: list(x["revision"]) for k, x in md["cache"].items()}
            machine_eq["cache_policy"] = all(CORE.cached_policy_part(mj["cache"][k]["probe"])
                                             == CORE.cached_policy_part(md["cache"][k]["probe"]) for k in md["cache"])
            machine_eq["last_probe_policy"] = all(CORE.cached_policy_part(mj["last_probe"][k])
                                                  == CORE.cached_policy_part(md["last_probe"][k]) for k in md["last_probe"])
            machine_eq["quiet_probe_policy"] = set(mj["quiet_probe"]) == set(md["quiet_probe"]) and all(
                CORE.cached_policy_part(mj["quiet_probe"][k]) == CORE.cached_policy_part(md["quiet_probe"][k])
                for k in md["quiet_probe"])
            machine_eq["no_event_reemitted"] = m.events == []
            if not all(machine_eq.values()):
                problems.append(f"the resumed machine differs from the frozen NS1d M2 machine: "
                                f"{[k for k, x in machine_eq.items() if not x]}")
            # -- the next decision (a copy), compared with the frozen NS1d M2 next decision at full precision
            dry = PH.SceneMachine.from_json(json.loads(json.dumps(m.to_json())))
            plan = dry.decide(K.refuse_gate)
            t_ = plan.get("target_id")
            nxt = K.plan_action(plan, outs.get(t_) if t_ is not None else None)
            frozen_next = read_json(SP.NS1D_RUN / "replay/final.json")["next_decisions"]["M2"]
            keys = ("kind", "target", "decision", "reason", "source", "local_gaze_deg", "world_gaze_deg")
            next_eq = {kk: CORE.jsonable(nxt.get(kk)) == CORE.jsonable(frozen_next.get(kk)) for kk in keys}
            exp = SP.HANDOFF_EXPECTED["next"]
            next_exp = {kk: CORE.jsonable(nxt.get(kk)) == CORE.jsonable(exp[kk]) for kk in exp}
            cal0 = json.loads(CORE.resolve(recs["172"]["looks"][0]["calibration"], run).read_text())
            hr, ho = head_pose(cal0)
            plan_g = None
            if t_ is not None:
                plan_g = C2.plan_action(outs[t_]["proposal"], charts[str(t_)], hr, ho)
                plan_g.pop("planned_calibration_bytes")
                plan_g.pop("planned_calibration")
                if (plan_g["roundtrip_error_deg"] > SP.GAZE_ROUNDTRIP_TOL_DEG
                        or plan_g["world_gaze_deg"] != nxt["world_gaze_deg"]
                        or not plan_g["physical_calibration_test"]["ok"]):
                    problems.append("the next action's world gaze / planned real-sensor calibration fails")
            if not all(next_eq.values()) or not all(next_exp.values()):
                problems.append(f"HARD STOP: the next decision is not the frozen NS1d M2 decision: {nxt} vs {frozen_next}")
            # -- the expected start state (derived, compared)
            hx = SP.HANDOFF_EXPECTED
            state_exp = {
                "current": m.current == hx["current"], "global_step": m.step == hx["global_step"],
                "attention_bout": m.bout == hx["attention_bout"],
                "own_looks": {str(i): int(recs[str(i)]["own_looks"]) for i in ids} == hx["own_looks"],
                "quiet": sorted(quiet) == hx["quiet"], "quiet_since": {str(k): v for k, v in m.quiet_since.items()}
                == hx["quiet_since"], "memory_total": summ["total_points"] == hx["memory_total"],
                "memory_ids": len(summ["instance_ids"]) == hx["memory_ids"],
                "revisions": {str(i): CORE.revision_m2(recs[str(i)], ledger) for i in ids} == hx["revisions"],
                "202_actionable": m.statuses[202].label == "ACTIONABLE", "172_quiet": m.statuses[172].label == "QUIET"}
            if not all(state_exp.values()):
                problems.append(f"the start state differs from the expectation: {[k for k, x in state_exp.items() if not x]}")
            # -- the derived hard cap
            cap = CORE.derive_cap(m)
            cap_ok = (cap["assumptions_ok"] and cap["budget"] == SP.BUDGET_EXPECTED
                      and cap["max_new_physical_actions"] == SP.MAX_NEW_EXPECTED
                      and cap["absolute_action_cap"] == SP.ABS_CAP_EXPECTED)
            if not cap_ok:
                problems.append(f"the derived cap {cap['max_new_physical_actions']} / {cap['absolute_action_cap']} "
                                f"differs from {SP.MAX_NEW_EXPECTED} / {SP.ABS_CAP_EXPECTED}")
            write_json(run / "handoff/cap.json", {"schema": "NS1e-cap-v1", "truth": SP.TRUTH_DERIVED, **cap,
                                                  "expected": {"max_new": SP.MAX_NEW_EXPECTED,
                                                               "absolute": SP.ABS_CAP_EXPECTED}, "ok": cap_ok,
                                                  "statement": "derived from the handoff machine and the live budget; "
                                                               "reaching it before closure is INCOMPLETE and never "
                                                               "permission to raise it"})
            # -- the initial scene state
            ents = {}
            for k in sorted(recs, key=int):
                i = int(k)
                rec = {kk: vv for kk, vv in recs[k].items() if kk not in ("probe", "status", "proposal", "policy",
                                                                          "revision")}
                rec["probe"] = written[i]
                rec["planar_support_last_look"] = planar[k]
                rec["revision"] = CORE.revision_m2(rec, ledger)
                rec["memory"] = CORE.memory_counts(rec, ledger)
                ents[k] = with_status(rec, m.statuses[i], outs[i])
            mem_block = {"events": ev_rows, "summary": summ, "digest": CORE.ledger_digest(summ),
                         "measured_points": {str(kk): int(vv) for kk, vv in sorted(ledger.measured_points.items())}}
            scene = {"schema": "NS1e-scene-state-v1", "truth": SP.TRUTH_DERIVED, "label": "initial",
                     "statement": "the accepted post-NS1c2-step-7 scene enriched by the accepted NS1d M2 memory after "
                                  "memory event 8; nothing re-acquired or re-rendered", "code": cs,
                     "last_global_step": int(m.step) - 1, "next_global_step": int(m.step), "phase": m.phase.value,
                     "current": int(m.current), "attention_bout": int(m.bout),
                     "executed_actions_total": SP.NS1D_EVENTS, "new_actions": 0, "budget": budget,
                     "cap": {"max_new": cap["max_new_physical_actions"], "absolute": cap["absolute_action_cap"]},
                     "scene_ids": ids, "ambiguous": [{"temporary_entity_id": a, "state": SP.AMBIGUOUS_STATE,
                                                      "in_scheduler": False} for a in el["deferred_ids"]],
                     "entities": ents, "machine": m.to_json(), "memory": mem_block,
                     "map_digest": CORE.map_digest(ents), "events": [], "last_action": None,
                     "next_decision_reproduced": nxt, "table": scene_table(ents), "gate_guard": gg.record()}
            write_json(run / SP.scene_state_rel("initial"), CORE.jsonable(scene))
            out = {"schema": "NS1e-handoff-v1", "truth": SP.TRUTH_DERIVED, "code": cs,
                   "statement": "the complete live M2 scene reconstructed independently from the frozen NS1c2 / NS1d "
                                "records, verified field by field, and the frozen next decision reproduced exactly before "
                                "any render", "eligibility": {"coherent": ids, "ambiguous": el["deferred_ids"]},
                   "charts_equal_ns1c2": all(c["equals_ns1c2_chart"] for c in charts.values()),
                   "contexts": ctx_eq, "memory_equal_ns1d": mem_equal, "memory_total": summ["total_points"],
                   "memory_ids": summ["instance_ids"], "probes": probe_eq, "machine_equal_ns1d": machine_eq,
                   "quiet_at_resume": quiet, "quiet_since": {str(k): v for k, v in m.quiet_since.items()},
                   "next_decision": nxt, "next_decision_frozen": frozen_next, "next_equal_frozen": next_eq,
                   "next_equal_expected": next_exp, "next_plan_geometry": plan_g, "start_state_expected": state_exp,
                   "cap": {"max_new": cap["max_new_physical_actions"], "absolute": cap["absolute_action_cap"],
                           "ok": cap_ok}, "gate_guard": gg.record(), "problems": problems, "ok": not problems}
            write_json(run / "handoff/handoff.json", CORE.jsonable(out))
            files = sorted(str(p.relative_to(run)) for p in (run / "handoff").rglob("*") if p.is_file()
                           and p.name != "handoff-opened-files.json") + [SP.scene_state_rel("initial")]
            write_json(run / "freeze/handoff-freeze.json", {
                "schema": "NS1e-handoff-freeze-v1", "truth": SP.TRUTH_DERIVED, "frozen_utc": utc(), "code": cs,
                "ok": not problems, "statement": "the start state, charts, eligibility, cap and next decision, frozen "
                                                 "before any NS1e render", "files": {fl: sha256(run / fl) for fl in files}})
    finally:
        write_json(run / "handoff/handoff-opened-files.json", guard_record(g, pg))
    if problems:
        raise SystemExit(f"{PREFIX} HARD STOP handoff (no render): {problems}")
    return {"current": out["next_decision"]["target"], "next": [out["next_decision"]["source"],
                                                                out["next_decision"]["local_gaze_deg"]],
            "memory": out["memory_total"], "cap": out["cap"], "quiet": out["quiet_at_resume"]}


# ------------------------------------------------------------------ gate-harness (contract section 12; no render)
def require_handoff(run: Path) -> dict:
    need(run / "freeze/handoff-freeze.json", "handoff")
    fz = read_json(run / "freeze/handoff-freeze.json")
    if not fz.get("ok"):
        raise Refused(f"{PREFIX} REFUSED the handoff did not pass")
    return fz


def gate_harness(ctx: Ctx) -> dict:
    run = ctx.run
    require_handoff(run)
    once(run / "gate-harness/gate-harness.json", "the gate-wiring harness")
    cs = require_committed(ctx, "gate-harness")
    import ns1b_chart as CH
    import ns1c2_phase as PH
    import ns1e_core as CORE
    from fov3d.control import controller02 as c2
    CH.ensure_policy_modules()
    import ns1a_core  # noqa: F401
    import fsg6f_frontier  # noqa: F401
    st = read_json(run / SP.scene_state_rel("initial"))
    reads = ([run / SP.scene_state_rel("initial"), run / "freeze/handoff-freeze.json", run / "handoff/charts.json"]
             + [run / f for f in read_json(run / "freeze/handoff-freeze.json")["files"]]
             + record_reads(st["entities"], run) + memory_reads(st["memory"]["events"], run))
    (run / "gate-harness").mkdir(parents=True, exist_ok=True)
    g = OpenGuard("ns1e-gate-harness", reads, [run / "gate-harness"])
    pg = no_process()
    problems, rows = [], []
    try:
        with g, pg:
            verify_record_hashes(run, "freeze/handoff-freeze.json")
            before = sha256(run / SP.scene_state_rel("initial"))
            ledger, _ev = ledger_from(st, run)
            require_memory_digest(ledger, st["memory"]["digest"], "the handoff memory")
            chs = read_json(run / "handoff/charts.json")["charts"]
            m = PH.SceneMachine.from_json(st["machine"])
            cyc = [int(k) for k in sorted(st["entities"], key=int) if st["entities"][k]["status"]["label"] == "ACTIONABLE"
                   and (st["entities"][k].get("proposal") or {}).get("source") == "cyclopean_epistemic"]
            picks = [int(st["current"])] + cyc[:1]
            cal0 = json.loads(res(st["entities"]["172"]["looks"][0]["calibration"], run).read_text())
            hr, ho = head_pose(cal0)
            for i in picks:
                rec = st["entities"][str(i)]
                cached = read_json(res(rec["probe"]["path"], run))["probe"]
                proposal = m.last_probe[i]
                refused_in_normal = False
                with PH.GateGuard(c2.ScenePhase.NORMAL.value, f"gate harness NORMAL refusal {i}") as gn:
                    try:
                        from fov3d.experiments.classroom_oracle import controller02 as x2
                        x2.final_look_gate_v1(proposal=proposal, decision=None, geometry=np.zeros((0, 3)), gaze=(0, 0),
                                              calibration={}, state={}, history=[], visited=[], profile=SP.PROFILE,
                                              head_r_wh=hr, head_origin_w=ho, target_id=i)
                    except PH.GateOutsideResidue:
                        refused_in_normal = True
                with PH.GateGuard(c2.ScenePhase.RESIDUE.value, f"gate harness RESIDUE {i}") as gr:
                    verdict, detail = CORE.residue_gate_m2(rec, run, chs[str(i)], cached, proposal, hr, ho, ledger,
                                                           f"gate harness entity {i}")
                p3 = detail["adapter"]["p3"]
                world = detail["proposal"]["world_gaze_deg"]
                local = detail["proposal"]["local_gaze_deg"]
                fake = CH.baseline_projected_sensor(SP.PROFILE, local[0], local[1], hr, ho)
                # every P3 call uses the real fixed-head sensor at the mapped world gaze; the gate traces (and so
                # predicts) an FSG6f proposal, while accepted v1 rejects a Cyclopean one before any prediction
                traced = proposal.action.source == "fsg6f"
                real_ok = all(max(abs(a - b) for a, b in zip(x["world_gaze_deg"], world)) <= 1e-12
                              and max(abs(a - b) for a, b in zip(x["calibration_gaze_deg"], world)) <= 1e-9
                              and x["tangent_frame"] == SP.TANGENT_FRAME for x in p3) and (bool(p3) if traced else
                                                                                          True)
                if not traced and (p3 or verdict.reason != "untraceable_final_support"):
                    real_ok = False
                fake_differs = max(abs(a - b) for a, b in zip(fake["gaze_yaw_pitch_deg"], world)) > 1e-6
                row = {"entity": i, "proposal": detail["proposal"], "verdict": {"admissible": verdict.admissible,
                                                                              "reason": verdict.reason},
                       "recomputed_probe_equal": detail["recomputed_probe_equal"], "p3_calls": len(p3),
                       "p3_real_h0_sensor": real_ok, "traced_by_gate": traced, "fake_local_sensor_differs": fake_differs,
                       "gate_guard_residue": gr.record(), "gate_guard_normal": gn.record(),
                       "refused_in_normal": refused_in_normal, "effective_points": detail["effective_points"],
                       "detail": detail["detail"]}
                rows.append(row)
                if not (detail["recomputed_probe_equal"] and real_ok and fake_differs and refused_in_normal
                        and gr.record()["normal_calls"] == 0 and gr.record()["residue_calls"] == 1):
                    problems.append(f"entity {i}: the gate wiring fails {row['verdict']} p3 {real_ok}")
            after = sha256(run / SP.scene_state_rel("initial"))
            out = {"schema": "NS1e-gate-harness-v1", "truth": SP.TRUTH_DERIVED, "code": cs,
                   "statement": "WIRING EVIDENCE ONLY: the M2 residue-gate adapter driven on copies of the frozen "
                                "handoff state in RESIDUE phase; no action is taken and nothing enters the scene",
                   "entities": rows, "state_unchanged": before == after, "problems": problems,
                   "ok": not problems and before == after}
            write_json(run / "gate-harness/gate-harness.json", CORE.jsonable(out))
    finally:
        write_json(run / "gate-harness/gate-harness-opened-files.json", guard_record(g, pg))
    if not out["ok"]:
        raise SystemExit(f"{PREFIX} STOP gate harness: {problems}")
    return {"entities": [[r["entity"], r["verdict"]["admissible"], r["verdict"]["reason"]] for r in rows]}


# ------------------------------------------------------------------ the scene state before a step
def prev_state_rel(run: Path, k: int) -> str:
    st0 = read_json(run / SP.scene_state_rel("initial"))
    if int(k) == int(st0["next_global_step"]):
        return SP.scene_state_rel("initial")
    return SP.state_after(int(k) - 1)


def require_checkpoint(run: Path, k: int) -> None:
    if not (run / prev_freeze_rel(run, k)).is_file():
        raise Refused(f"{PREFIX} REFUSED the checkpoint before step {k} is not frozen")


def prev_freeze_rel(run: Path, k: int) -> str:
    st0 = read_json(run / SP.scene_state_rel("initial"))
    return "freeze/handoff-freeze.json" if int(k) == int(st0["next_global_step"]) else SP.checkpoint_rel(int(k) - 1)


def control_stopped(run: Path) -> bool:
    return (run / "scene/terminal.json").exists() or (run / "freeze/control-freeze.json").exists()


def require_action(ctx: Ctx, what: str) -> dict:
    sd = ctx.sd()
    need(sd / "freeze/plan-freeze.json", f"schedule (step {ctx.step})")
    d = read_json(sd / "plan/decision.json")
    if d.get("kind") not in ("attend", "final_residue") or not d.get("action"):
        raise Refused(f"{PREFIX} REFUSED {what} is not applicable: step {ctx.step} has no scheduled action")
    return d


def verify_plan_freeze(sd: Path) -> dict:
    fz = read_json(sd / "freeze/plan-freeze.json")
    for rel, h in fz["files"].items():
        if sha256(sd / rel) != h:
            raise SystemExit(f"{PREFIX} STOP {rel} differs from the plan freeze")
    return fz


def observation_files() -> list[str]:
    return [SP.ACQ_RUN_REL] + [f"{SP.OBS_ACQ}/{n}" for n in SP.OBS_ACQ_FILES] + [f"{SP.OBS_AID}/{n}"
                                                                                 for n in SP.OBS_AID_FILES]


# ------------------------------------------------------------------ schedule (the accepted Controller-02 decision; plan freeze)
def schedule(ctx: Ctx) -> dict:
    run, k = ctx.run, int(ctx.step)
    sd = ctx.sd()
    require_handoff(run)
    if not ctx.dev or (run / "gate-harness/gate-harness.json").exists():
        need(run / "gate-harness/gate-harness.json", "gate-harness")
        if not read_json(run / "gate-harness/gate-harness.json").get("ok"):
            raise Refused(f"{PREFIX} REFUSED the gate-wiring harness did not pass")
    if control_stopped(run):
        raise Refused(f"{PREFIX} REFUSED the scene already reached its terminal record")
    prel, pfz = prev_state_rel(run, k), prev_freeze_rel(run, k)
    need(run / prel, f"the scene checkpoint before step {k}")
    need(run / pfz, f"the checkpoint freeze before step {k}")
    if sd.exists() or (run / SP.step_dir(k + 1)).exists() or (run / SP.state_after(k)).exists():
        raise Refused(f"{PREFIX} REFUSED step {k} is not the next step (its directory or a later one exists)")
    cs = require_committed(ctx, "schedule")
    import ns1b_chart as CH
    import ns1c2_core as C2
    import ns1c2_phase as PH
    import ns1e_core as CORE
    from fov3d.control import controller02 as c2
    CH.ensure_policy_modules()
    import ns1a_core  # noqa: F401
    import fsg6f_frontier  # noqa: F401
    prev = read_json(run / prel)
    reads = ([run / prel, run / pfz, run / "handoff/charts.json", run / "handoff/cap.json"]
             + [run / f for f in read_json(run / pfz)["files"]]
             + record_reads(prev["entities"], run) + memory_reads(prev["memory"]["events"], run))
    (sd / "plan").mkdir(parents=True, exist_ok=True)
    (sd / "freeze").mkdir(parents=True, exist_ok=True)
    g = OpenGuard(f"ns1e-schedule-{k:03d}", reads, [sd / "plan", sd / "freeze", run / "scene"])
    pg = no_process()
    terminal = None
    try:
        with g, pg, PH.GateGuard(prev["phase"], f"schedule step {k}") as gg:
            verify_record_hashes(run, pfz)
            ledger, events = ledger_from(prev, run)
            require_memory_digest(ledger, prev["memory"]["digest"], f"the checkpoint before step {k}")
            if CORE.map_digest(prev["entities"]) != prev["map_digest"]:
                raise SystemExit(f"{PREFIX} STOP the map digest of the checkpoint does not reproduce")
            capr = read_json(run / "handoff/cap.json")
            abs_cap = int(capr["absolute_action_cap"])
            chs = read_json(run / "handoff/charts.json")["charts"]
            m = PH.SceneMachine.from_json(prev["machine"])
            if int(m.step) != k:
                raise SystemExit(f"{PREFIX} STOP the machine's global step {m.step} is not {k}")
            statuses = [[int(s.instance_id), s.label] for s in sorted(m.statuses.values(), key=lambda s: s.instance_id)]
            sched = c2.schedule_normal(m.current, m.statuses.values())
            cal0 = json.loads(res(prev["entities"]["172"]["looks"][0]["calibration"], run).read_text())
            hr, ho = head_pose(cal0)
            gate_records = []

            def final_gate(i, proposal):
                gg.phase = m.phase.value
                rec = prev["entities"][str(i)]
                cached = read_json(res(rec["probe"]["path"], run))["probe"]
                verdict, detail = CORE.residue_gate_m2(rec, run, chs[str(i)], cached, proposal, hr, ho, ledger,
                                                       f"residue gate entity {i} (step {k})")
                gate_records.append({"object": int(i), "phase": m.phase.value, "global_step": k,
                                     "revision": CORE.revision_m2(rec, ledger), **detail})
                return verdict
            n_ev = len(m.events)
            plan = m.decide(final_gate, abs_cap)
            mem_summary = {"events": len(events), "digest": prev["memory"]["digest"],
                           "total_points": prev["memory"]["summary"]["total_points"]}
            out = {"schema": "NS1e-decision-v1", "truth": SP.TRUTH_DERIVED, "code": cs, "global_step": k,
                   "kind": plan["kind"],
                   "statement": "the accepted Controller-02 scene machine (controller02.schedule_normal over "
                                "NORMAL-serviceable objects; RESIDUE only when it returns None), frozen before any render",
                   "scheduler_decision": {"function": "fov3d.control.controller02.schedule_normal",
                                          "current_before": prev["current"], "statuses": statuses,
                                          "result": None if sched is None else {"kind": sched.kind,
                                                                                "target_id": sched.target_id,
                                                                                "reason": sched.reason}},
                   "phase_before": prev["phase"], "phase_after_decide": m.phase.value,
                   "events_in_decide": m.events[n_ev:], "residue_gate_records": gate_records,
                   "gate_guard": gg.record(), "new_actions_before": prev["new_actions"],
                   "cap": {"absolute": abs_cap, "max_new": int(capr["max_new_physical_actions"])},
                   "service_states": {str(s[0]): s[1] for s in statuses}, "map_digest": prev["map_digest"],
                   "memory": mem_summary,
                   "scene_state_before": {"path": prel, "sha256": sha256(run / prel)}}
            if plan["kind"] in ("closed", "cap"):
                terminal = plan
                out["terminal"] = CORE.jsonable({k_: v for k_, v in plan.items()})
                out["machine_after_decide"] = m.to_json()
                out["statuses_after_decide"] = {str(i): C2.status_record(s) for i, s in m.statuses.items()}
                write_json(sd / "plan/decision.json", CORE.jsonable(out))
                write_json(run / "scene/terminal.json", CORE.jsonable({
                    **out, "label": "terminal", "outcome": CORE.control_outcome(out["terminal"]),
                    "terminal_breakdown": CORE.terminal_breakdown(
                        out["terminal"].get("closure") or {}, out["statuses_after_decide"])
                    if plan["kind"] == "closed" else None}))
            else:
                t = int(plan["target_id"])
                rec_t = prev["entities"][str(t)]
                pf = res(rec_t["probe"]["path"], run)
                if sha256(pf) != rec_t["probe"]["sha256"]:
                    raise SystemExit(f"{PREFIX} STOP the probe record of {t} changed")
                prop = read_json(pf)["probe"]["proposal"]
                a = plan["action"]
                if prop is None or list(a.gaze_yaw_pitch_deg) != list(prop["local_gaze_deg"]) or a.source != prop["source"]:
                    raise SystemExit(f"{PREFIX} STOP the adapter's action is not the target's unchanged current proposal")
                plan_g = C2.plan_action(prop, chs[str(t)], hr, ho)
                if (plan_g["roundtrip_error_deg"] > SP.GAZE_ROUNDTRIP_TOL_DEG
                        or plan_g["world_gaze_deg"] != prop["world_gaze_deg"]
                        or not plan_g["physical_calibration_test"]["ok"]):
                    raise SystemExit(f"{PREFIX} STOP the world gaze / planned calibration of step {k} fails (Outcome 3)")
                b = plan_g.pop("planned_calibration_bytes")
                planned = plan_g.pop("planned_calibration")
                (sd / "plan/planned-calibration.json").write_bytes(b)
                e = len(events)
                first_r1 = (t in SP.RANK1 and int(rec_t["own_looks"]) == 1)
                out["plan"] = plan_to_json(plan)
                out["machine_after_decide"] = m.to_json()
                out["scheduler_reason"] = plan["reason"]
                out["attention_bout"] = plan["attention_bout"]
                out["action"] = {"global_step": k, "kind": plan["kind"], "phase": plan["phase"], "target": t,
                                 "decision": plan["decision"], "reason": plan["reason"], "source": prop["source"],
                                 "local_gaze_deg": plan_g["local_gaze_deg"], "world_gaze_deg": plan_g["world_gaze_deg"],
                                 "planned_calibration_sha256": hashlib.sha256(b).hexdigest(),
                                 "patch_id": SP.patch_id(k), "memory_event": e,
                                 "memory_event_expected": SP.memory_event_of_step(k),
                                 "own_looks_before": rec_t["own_looks"], "chart_id": rec_t["chart_id"],
                                 "chart_sha256": rec_t["chart_sha256"], "target_revision": rec_t["revision"],
                                 "proposal_probe": rec_t["probe"], "status_before": rec_t["status"]}
                out["plan_geometry"] = {**plan_g, "planned_gaze_H0_deg": list(planned["gaze_yaw_pitch_deg"])}
                out["previous_target"] = prev["current"]
                out["target_transition"] = "retain" if prev["current"] == t else f"{prev['current']}->{t}"
                if first_r1:
                    out["rank1_first_selection"] = {
                        "target": t, "own_planar_support": rec_t.get("planar_support_last_look"),
                        "m2_effective_points": rec_t["memory"]["effective_points"], "source": prop["source"],
                        "local_gaze_deg": plan_g["local_gaze_deg"], "world_gaze_deg": plan_g["world_gaze_deg"]}
                if e != SP.memory_event_of_step(k):
                    raise SystemExit(f"{PREFIX} STOP memory event {e} is not the event of step {k}")
                write_json(sd / "plan/decision.json", CORE.jsonable(out))
                frozen = {kk: out[kk] for kk in ("global_step", "kind", "scheduler_decision", "phase_after_decide",
                                                  "service_states", "map_digest", "memory")}
                frozen["action"] = out["action"]
                write_json(sd / "freeze/plan-freeze.json", {
                    "schema": "NS1e-plan-freeze-v1", "truth": SP.TRUTH_DERIVED, "frozen_utc": utc(), "code": cs,
                    "global_step": k, "statement": "the controller plan, frozen BEFORE the render",
                    "plan_digest": CORE.canonical_digest(frozen),
                    "files": {rel: sha256(sd / rel) for rel in ("plan/decision.json", "plan/planned-calibration.json")}})
    finally:
        write_json(sd / "plan/plan-opened-files.json", guard_record(g, pg))
    if terminal is not None:
        return {"kind": terminal["kind"]}
    return {"kind": out["kind"], "target": out["action"]["target"], "reason": out["scheduler_reason"],
            "phase": out["action"]["phase"], "source": out["action"]["source"],
            "local": out["action"]["local_gaze_deg"], "world": out["action"]["world_gaze_deg"]}


# ------------------------------------------------------------------ Blender (preflight / acquire of a step)
def blender(ctx: Ctx, args: list[str], log: Path, factory: bool = False) -> None:
    log.parent.mkdir(parents=True, exist_ok=True)
    cmd = [SP.BLENDER, "-b"] + (["--factory-startup"] if factory else [str(REPO / SP.BLEND)])
    cmd += ["--python-exit-code", "1", "-P", str(HERE / "ns1e_render.py"), "--"] + args
    with open(log, "w") as f:
        p = subprocess.run(cmd, cwd=REPO, stdout=f, stderr=subprocess.STDOUT)
    text = log.read_text(errors="replace")
    if p.returncode != 0 or "[ns1e-render] COMPLETE" not in text or "[ns1e-render] FAILED" in text:
        raise SystemExit(f"{PREFIX} STOP Blender failed (exit {p.returncode}); see {log}")


def preflight(ctx: Ctx) -> dict:
    sd = ctx.sd()
    require_action(ctx, "preflight")
    verify_plan_freeze(sd)
    once(sd / "preflight/preflight.json", f"the preflight of step {ctx.step}")
    require_committed(ctx, "preflight")
    if ctx.rehearsal_spp is None:
        if sha256(REPO / SP.BLEND) != SP.BLEND_SHA256:
            raise SystemExit(f"{PREFIX} STOP the Classroom blend changed")
        blender(ctx, ["--mode", "preflight", "--step-dir", str(sd)], sd / "preflight/blender.log")
    else:
        write_json(sd / "preflight/preflight.json", {"schema": "NS1e-preflight-v1", "rendered": False,
                                                       "rehearsal": True, "statement": "rehearsal: no Classroom"})
    return {k: v for k, v in read_json(sd / "preflight/preflight.json").items() if k in ("rendered", "gaze_H0_deg")}


def acquire(ctx: Ctx) -> dict:
    sd = ctx.sd()
    d = require_action(ctx, "acquire")
    verify_plan_freeze(sd)
    need(sd / "preflight/preflight.json", "preflight")
    if read_json(sd / "preflight/preflight.json").get("rendered") is not False:
        raise SystemExit(f"{PREFIX} STOP the preflight record is not a no-render record")
    if ctx.rehearsal_spp is not None and not ctx.dev:
        raise SystemExit(f"{PREFIX} STOP the rehearsal acquisition is a --dev command")
    once(sd / "observation", f"the physical observation of step {ctx.step} (never re-rendered)")
    require_committed(ctx, "acquire")
    if ctx.rehearsal_spp is None:
        if sha256(REPO / SP.BLEND) != SP.BLEND_SHA256:
            raise SystemExit(f"{PREFIX} STOP the Classroom blend changed")
        blender(ctx, ["--mode", "canonical", "--step-dir", str(sd)], sd / "acquisition-blender.log")
    else:
        blender(ctx, ["--mode", "rehearsal", "--step-dir", str(sd), "--spp", str(int(ctx.rehearsal_spp))],
                sd / "acquisition-blender.log", factory=True)
    ar = read_json(sd / SP.ACQ_RUN_REL)
    for rel in [f"{SP.OBS_ACQ}/{n}" for n in SP.OBS_ACQ_FILES] + [f"{SP.OBS_AID}/{n}" for n in SP.OBS_AID_FILES]:
        need(sd / rel, rel)
    if list(ar["gaze_H0_deg"]) != list(d["action"]["world_gaze_deg"]):
        raise SystemExit(f"{PREFIX} STOP the executed gaze differs from the decision")
    return {"gaze_H0_deg": ar["gaze_H0_deg"], "render_seconds_lr": ar["render_seconds_lr"], "spp": ar["spp"],
            "target": ar["target"]}


# ------------------------------------------------------------------ freeze-observation / PERFECT correspondence / geometry / id
def freeze_observation(ctx: Ctx) -> dict:
    sd = ctx.sd()
    d = require_action(ctx, "freeze-observation")
    need(sd / SP.ACQ_RUN_REL, "acquire")
    once(sd / "freeze/observation-freeze.json", f"the observation freeze of step {ctx.step}")
    cs = require_committed(ctx, "freeze-observation")
    files = observation_files()
    g = OpenGuard(f"ns1e-freeze-observation-{ctx.step:03d}", [sd / f for f in files] + [
        sd / "plan/planned-calibration.json", sd / "plan/decision.json", sd / "plan/planned-calibration.json", sd / "freeze/plan-freeze.json"], [sd / "freeze"])
    pg = no_process(light=True)
    try:
        with g, pg:
            verify_plan_freeze(sd)
            hashes = {f: sha256(sd / f) for f in files}
            ar = read_json(sd / SP.ACQ_RUN_REL)
            rec = read_json(sd / f"{SP.OBS_ACQ}/acquisition.json")
            problems = []
            for key, rel in (("calibration_sha256", f"{SP.OBS_ACQ}/calibration.json"),
                             ("rgb_observation_sha256", f"{SP.OBS_ACQ}/rgb-observation.npz"),
                             ("reference_observation_sha256", f"{SP.OBS_AID}/reference-observation.npz")):
                if ar[key] != hashes[rel]:
                    problems.append(key)
            if (sd / f"{SP.OBS_ACQ}/calibration.json").read_bytes() != (sd / "plan/planned-calibration.json").read_bytes():
                problems.append("calibration bytes != the planned calibration")
            if hashes[f"{SP.OBS_ACQ}/calibration.json"] != d["action"]["planned_calibration_sha256"]:
                problems.append("calibration != the decision's planned calibration")
            if (rec["spp"] != ar["spp"] or rec["render_seeds_lr"] != SP.SEEDS or rec["device"] != SP.DEVICE
                    or rec["settings"]["samples"] != ar["spp"]
                    or list(rec["gaze_yaw_pitch_deg"]) != list(d["action"]["world_gaze_deg"])
                    or int(rec["target"]) != int(d["action"]["target"])):
                problems.append("acquisition record")
            physical = {"denoising_off": rec["settings"]["denoising"] is False,
                        "adaptive_off": rec["settings"]["adaptive_sampling"] is False,
                        "box_filter": rec["settings"]["pixel_filter"] == "BOX" and rec["settings"]["filter_width"] == 1.0}
            if not ctx.dev:
                physical.update({"spp": ar["spp"] == SP.SPP,
                                 "exr_samples": ar["exr_samples_lr"] == {"L": str(SP.SPP), "R": str(SP.SPP)},
                                 "catalog_seal": ar["catalog_seal"]["sha256"] == SP.NS1A_CATALOG_SEAL,
                                 "not_rehearsal": not rec.get("rehearsal")})
            problems += [k_ for k_, v in physical.items() if not v]
            with np.load(sd / f"{SP.OBS_ACQ}/rgb-observation.npz") as z:
                if sorted(z.files) != ["rgb_L", "rgb_R"]:
                    problems.append(f"rgb keys {z.files}")
            with np.load(sd / f"{SP.OBS_AID}/reference-observation.npz") as z:
                if sorted(z.files) != sorted(("instance_L", "instance_R", "position_w_L", "position_w_R")):
                    problems.append(f"reference keys {z.files}")
            if problems:
                raise SystemExit(f"{PREFIX} STOP observation problems: {problems}")
            fz = {"schema": "NS1e-observation-freeze-v1", "truth": SP.TRUTH_ORACLE, "frozen_utc": utc(), "code": cs,
                  "global_step": ctx.step, "target": d["action"]["target"], "physical": physical,
                  "statement": "the step's one binocular observation at the mapped H0 gaze; never re-rendered. The "
                               "sealed catalog is NOT opened: its Blender-recorded seal is carried", "spp": ar["spp"],
                  "catalog_seal": ar["catalog_seal"], "files": hashes}
            write_json(sd / "freeze/observation-freeze.json", fz)
    finally:
        write_json(sd / "freeze/observation-freeze-opened-files.json", guard_record(g, pg))
    return {"files": len(hashes), "spp": ar["spp"]}


def perfect_correspondence(ctx: Ctx) -> dict:
    sd = ctx.sd()
    require_action(ctx, "perfect-correspondence")
    need(sd / "freeze/observation-freeze.json", "freeze-observation")
    once(sd / "correspondence", f"the perfect correspondence of step {ctx.step}")
    require_committed(ctx, "perfect-correspondence")
    import ab1b_oracle as O   # accepted AB1b oracle, read-only (imported before the guard)
    import fsg_geometry  # noqa: F401
    import ns1a_core as NCORE
    cal, ref = sd / f"{SP.OBS_ACQ}/calibration.json", sd / f"{SP.OBS_AID}/reference-observation.npz"
    odir = sd / "correspondence"
    odir.mkdir(parents=True, exist_ok=True)
    g = OpenGuard(f"ns1e-oracle-{ctx.step:03d}", [cal, ref, sd / "freeze/observation-freeze.json"], [odir])
    pg = no_process(light=True)
    try:
        with g, pg:
            fz = read_json(sd / "freeze/observation-freeze.json")
            inputs = {}
            for name, path, rel in (("calibration", cal, f"{SP.OBS_ACQ}/calibration.json"),
                                    ("reference_observation", ref, f"{SP.OBS_AID}/reference-observation.npz")):
                h = sha256(path)
                if h != fz["files"][rel]:
                    raise SystemExit(f"{PREFIX} STOP {name} changed after the observation freeze")
                inputs[name] = {"path": str(path), "sha256": h}
            c = read_json(cal)
            refd = O.load_reference(ref)
            product, summ = O.compute_oracle(c, refd)
            cls = NCORE.core_class_map(c, refd)
            corr = np.flatnonzero(cls.ravel() == 3)
            want = product["left_core_row"].astype(np.int64) * SP.CORE_SIZE + product["left_core_col"]
            if not np.array_equal(corr, want):
                raise SystemExit(f"{PREFIX} STOP the class map disagrees with the accepted product")
            np.savez_compressed(odir / "oracle-correspondences.npz", **product)
            np.savez_compressed(odir / "core-class-map.npz", core_class=cls)
            summary = {"schema": "NS1e-oracle-summary-v1", "truth": SP.TRUTH_DERIVED, "label": SP.LABEL_ORACLE_CORR,
                       "statement": "PERFECT / ORACLE CORRESPONDENCE (accepted AB1b compute_oracle, read-only): "
                                    "Position and Object Index were used here, and only here, to choose and project the "
                                    "matches; the product holds core row / col and continuous uv_L / uv_R only",
                       "oracle": O.SP.ORACLE, "oracle_config_sha256": O.SP.config_sha256(O.SP.ORACLE),
                       "inputs": inputs, "product_keys": sorted(product),
                       "core_class_counts": {str(kk): int((cls == kk).sum()) for kk in range(4)}, **summ}
            write_json(odir / "oracle-summary.json", summary)
    finally:
        write_json(odir / "correspondence-opened-files.json", guard_record(g, pg))
    return {"correspondences": summary["correspondences"]}


def freeze_correspondence(ctx: Ctx) -> dict:
    sd = ctx.sd()
    require_action(ctx, "freeze-correspondence")
    need(sd / "correspondence/oracle-summary.json", "perfect-correspondence")
    once(sd / "freeze/correspondence-freeze.json", f"the correspondence freeze of step {ctx.step}")
    cs = require_committed(ctx, "freeze-correspondence")
    import ab1b_geometry as BG
    g = OpenGuard(f"ns1e-freeze-correspondence-{ctx.step:03d}", [sd / f for f in SP.CORR_FILES], [sd / "freeze"])
    pg = no_process(light=True)
    try:
        with g, pg:
            rec = read_json(sd / "correspondence/correspondence-opened-files.json")
            want = {str((sd / f"{SP.OBS_ACQ}/calibration.json").resolve()),
                    str((sd / f"{SP.OBS_AID}/reference-observation.npz").resolve()),
                    str((sd / "freeze/observation-freeze.json").resolve())}
            if (rec["violations"] or set(rec["data_reads"]) != want or rec["modules_loaded"]["cv2"]
                    or rec["modules_loaded"]["fsg_stereo"] or rec["forbidden_reads"]
                    or (rec.get("process_guard") or {}).get("attempts")):
                raise SystemExit(f"{PREFIX} STOP the oracle guard record is not clean")
            BG.load_product(sd / "correspondence/oracle-correspondences.npz")
            fz = {"schema": "NS1e-correspondence-freeze-v1", "truth": SP.TRUTH_DERIVED, "frozen_utc": utc(), "code": cs,
                  "global_step": ctx.step,
                  "statement": "the truth-stripped perfect-correspondence product, frozen before the spherical geometry",
                  "files": {f: sha256(sd / f) for f in SP.CORR_FILES}}
            write_json(sd / "freeze/correspondence-freeze.json", fz)
    finally:
        write_json(sd / "freeze/correspondence-freeze-opened-files.json", guard_record(g, pg))
    return {"files": len(SP.CORR_FILES)}


def truth_reads(events: list[dict]) -> dict:
    paths = [e["path"] for e in events if e.get("event") == "open"]
    ref = [p for p in paths if p.endswith("reference-observation.npz") or p.endswith(".exr") or "/oracle_aid/" in p
           or "evaluation_only" in p]
    return {"position_reads": len(ref), "object_index_reads": len(ref),
            "catalog_reads": len([p for p in paths if "catalog" in p])}


def spherical_geometry(ctx: Ctx) -> dict:
    sd = ctx.sd()
    require_action(ctx, "spherical-geometry")
    if not (sd / "freeze/correspondence-freeze.json").exists():   # existence only (no read); hashes in freeze-geometry
        raise Refused(f"{PREFIX} REFUSED freeze-correspondence comes first")
    once(sd / "geometry", f"the spherical geometry of step {ctx.step}")
    require_committed(ctx, "spherical-geometry")
    import ab1b_geometry as BG   # accepted AB1b geometry, read-only
    import fsg_geometry as FG
    cal, prod_p = sd / f"{SP.OBS_ACQ}/calibration.json", sd / "correspondence/oracle-correspondences.npz"
    odir = sd / "geometry"
    odir.mkdir(parents=True, exist_ok=True)
    g = OpenGuard(f"ns1e-geometry-{ctx.step:03d}", [cal, prod_p], [odir])
    pg = no_process(light=True)
    try:
        with g, pg:
            inputs = {"calibration": {"path": str(cal), "sha256": sha256(cal)},
                      "correspondences": {"path": str(prod_p), "sha256": sha256(prod_p)}}
            c = read_json(cal)
            FG.validate_calibration(c)
            prod = BG.load_product(prod_p)
            rays = BG.left_core_rays(c)
            r_ = BG.compute_epipolar(c, prod)
            np.savez_compressed(odir / "left-core-rays.npz", **rays)
            np.savez_compressed(odir / "epipolar-result.npz", **r_)
            summary = {"schema": "NS1e-geometry-summary-v1", "truth": SP.TRUTH_DERIVED, "label": SP.LABEL_GEOMETRY,
                       "statement": "TRUTH-FREE SPHERICAL EPIPOLAR RECONSTRUCTION (accepted AB1b geometry): the "
                                    "calibration and the frozen truth-stripped product only; canonical fixed-head H0",
                       "geometry": BG.SP.GEOMETRY, "geometry_config_sha256": BG.SP.config_sha256(BG.SP.GEOMETRY),
                       "inputs": inputs, "baseline_m": float(c["ipd_m"]), "focal_px": float(c["eyes"][0]["K"][0][0]),
                       **BG.summarize(c, rays, r_)}
            write_json(odir / "geometry-summary.json", summary)
    finally:
        rec = guard_record(g, pg)
        rec.update(truth_reads(rec["events"]))
        write_json(odir / "geometry-opened-files.json", rec)
    return {"triangulated": summary["counts"]["triangulated_epipolar"]}


def freeze_geometry(ctx: Ctx) -> dict:
    sd = ctx.sd()
    require_action(ctx, "freeze-geometry")
    need(sd / "geometry/geometry-summary.json", "spherical-geometry")
    once(sd / "freeze/geometry-freeze.json", f"the geometry freeze of step {ctx.step}")
    cs = require_committed(ctx, "freeze-geometry")
    cfz = sd / "freeze/correspondence-freeze.json"
    g = OpenGuard(f"ns1e-freeze-geometry-{ctx.step:03d}", [sd / f for f in SP.GEOM_FILES + SP.CORR_FILES] + [cfz],
                  [sd / "freeze"])
    pg = no_process(light=True)
    try:
        with g, pg:
            fzc = verify_record_hashes(sd, "freeze/correspondence-freeze.json")
            rec = read_json(sd / "geometry/geometry-opened-files.json")
            summ = read_json(sd / "geometry/geometry-summary.json")
            prod_rel = "correspondence/oracle-correspondences.npz"
            want = {str((sd / f"{SP.OBS_ACQ}/calibration.json").resolve()), str((sd / prod_rel).resolve())}
            if (rec["violations"] or set(rec["data_reads"]) != want or any(rec["modules_loaded"][m] for m in (
                    "cv2", "fsg_stereo", "ab1a_stereo", "ab1d_match", "ab1d3_sgbm", "ab1b_oracle", "fsg6f_frontier",
                    "fov3d.control.integrated", "fov3d.control.controller02"))
                    or rec["position_reads"] or rec["object_index_reads"] or rec["catalog_reads"]
                    or summ["inputs"]["correspondences"]["sha256"] != fzc["files"][prod_rel]):
                raise SystemExit(f"{PREFIX} STOP the geometry guard record or input is not clean")
            fz = {"schema": "NS1e-geometry-freeze-v1", "truth": SP.TRUTH_DERIVED, "frozen_utc": utc(), "code": cs,
                  "global_step": ctx.step,
                  "statement": "the truth-free spherical geometry, frozen before any identity is attached",
                  "correspondence_freeze_sha256": sha256(cfz), "files": {f: sha256(sd / f) for f in SP.GEOM_FILES}}
            write_json(sd / "freeze/geometry-freeze.json", fz)
    finally:
        write_json(sd / "freeze/geometry-freeze-opened-files.json", guard_record(g, pg))
    return {"files": len(SP.GEOM_FILES)}


def local_oracle_segmentation(ctx: Ctx) -> dict:
    sd = ctx.sd()
    require_action(ctx, "local-oracle-segmentation")
    need(sd / "freeze/geometry-freeze.json", "freeze-geometry")
    once(sd / "segmentation", f"the local oracle segmentation of step {ctx.step}")
    require_committed(ctx, "local-oracle-segmentation")
    import ns1a_core as NCORE
    odir = sd / "segmentation"
    odir.mkdir(parents=True, exist_ok=True)
    reads = [sd / "freeze/geometry-freeze.json"] + [sd / f for f in SP.GEOM_FILES] + [
        sd / "correspondence/oracle-correspondences.npz", sd / f"{SP.OBS_AID}/reference-observation.npz"]
    g = OpenGuard(f"ns1e-segmentation-{ctx.step:03d}", reads, [odir])
    pg = no_process(light=True)
    try:
        with g, pg:
            verify_record_hashes(sd, "freeze/geometry-freeze.json")
            g.mark("geometry_freeze_verified")
            g.mark("identity_access_begins")
            prod = load_npz(sd / "correspondence/oracle-correspondences.npz")
            r_ = read_members(sd / "geometry/epipolar-result.npz", ("valid_epi",))
            ref = read_members(sd / f"{SP.OBS_AID}/reference-observation.npz", SP.SEGMENTATION_MEMBERS)
            ids = NCORE.attach_identity(prod, r_["valid_epi"], ref["instance_L"])
            np.savez_compressed(odir / "local-identity.npz", left_core_row=prod["left_core_row"],
                                left_core_col=prod["left_core_col"], temporary_entity_id=ids,
                                valid=np.asarray(r_["valid_epi"], bool))
            summ = {"schema": "NS1e-identity-summary-v1", "truth": SP.TRUTH_DERIVED, "label": SP.LABEL_SEGMENTATION,
                    "statement": "ORACLE SEGMENTATION AID: temporary_entity_id = the left raw-core Object Index at the "
                                 "exact uv_L centre of each valid correspondence; not natural identity; no catalog, no "
                                 "names", "reference_members_read": list(SP.SEGMENTATION_MEMBERS),
                    **NCORE.identity_summary(ids)}
            write_json(odir / "identity-summary.json", summ)
    finally:
        write_json(odir / "segmentation-opened-files.json", guard_record(g, pg, {"reference_members_read":
                                                                                  list(SP.SEGMENTATION_MEMBERS)}))
    return {"entities": len(summ["entities"])}


def freeze_identity(ctx: Ctx) -> dict:
    sd = ctx.sd()
    require_action(ctx, "freeze-identity")
    need(sd / "segmentation/identity-summary.json", "local-oracle-segmentation")
    once(sd / "freeze/identity-freeze.json", f"the identity freeze of step {ctx.step}")
    cs = require_committed(ctx, "freeze-identity")
    gfz = sd / "freeze/geometry-freeze.json"
    g = OpenGuard(f"ns1e-freeze-identity-{ctx.step:03d}", [sd / f for f in SP.SEG_FILES] + [gfz], [sd / "freeze"])
    pg = no_process(light=True)
    try:
        with g, pg:
            rec = read_json(sd / "segmentation/segmentation-opened-files.json")
            marks = [e["label"] for e in rec["events"] if e.get("event") == "mark"]
            first_ref = next((n for n, e in enumerate(rec["events"]) if e.get("event") == "open"
                              and e["path"].endswith("reference-observation.npz")), None)
            mark_pos = next((n for n, e in enumerate(rec["events"]) if e.get("label") == "identity_access_begins"), None)
            ok = (not rec["violations"] and marks[:2] == ["geometry_freeze_verified", "identity_access_begins"]
                  and first_ref is not None and mark_pos is not None and mark_pos < first_ref
                  and rec.get("reference_members_read") == list(SP.SEGMENTATION_MEMBERS)
                  and not rec["forbidden_reads"] and not (rec.get("process_guard") or {}).get("attempts"))
            if not ok:
                raise SystemExit(f"{PREFIX} STOP the identity guard record is not clean (order / members / reads)")
            fz = {"schema": "NS1e-identity-freeze-v1", "truth": SP.TRUTH_DERIVED, "frozen_utc": utc(), "code": cs,
                  "global_step": ctx.step, "statement": "the local identity attachment, frozen after the geometry freeze "
                                                        "and before any fusion or memory",
                  "geometry_freeze_sha256": sha256(gfz), "files": {f: sha256(sd / f) for f in SP.SEG_FILES}}
            write_json(sd / "freeze/identity-freeze.json", fz)
    finally:
        write_json(sd / "freeze/identity-freeze-opened-files.json", guard_record(g, pg))
    return {"files": len(SP.SEG_FILES)}


# ------------------------------------------------------------------ target-only H0 fusion (section 15)
FUSION_FIELDS = ("action", "map_before", "map_after", "measured_points", "matched", "new", "affected_surfels",
                 "matched_distance_m", "patch_id", "target")


def fuse(ctx: Ctx) -> dict:
    run, sd, k = ctx.run, ctx.sd(), int(ctx.step)
    d = require_action(ctx, "fuse")
    need(sd / "freeze/identity-freeze.json", "freeze-identity")
    once(sd / "fusion", f"the H0 fusion of step {k}")
    cs = require_committed(ctx, "fuse")
    import ns1b_core as B
    import ns1c2_core as C2
    import ns1e_core as CORE
    from fov3d.reconstruction import surface_map as SMOD  # noqa: F401
    target = int(d["action"]["target"])
    prel = prev_state_rel(run, k)
    prev = read_json(run / prel)
    mrec = prev["entities"][str(target)]["map"]
    reads = [sd / "freeze/geometry-freeze.json", sd / "freeze/identity-freeze.json", sd / "freeze/observation-freeze.json",
             sd / "freeze/correspondence-freeze.json"] + [sd / f for f in SP.GEOM_FILES + SP.SEG_FILES] + [
        sd / "correspondence/oracle-correspondences.npz", sd / f"{SP.OBS_ACQ}/rgb-observation.npz",
        sd / "plan/decision.json", sd / "plan/planned-calibration.json", sd / "freeze/plan-freeze.json", run / prel,
        res(mrec["path"], run)] + freeze_reads(sd, ("freeze/geometry-freeze.json", "freeze/identity-freeze.json"))
    (sd / "fusion").mkdir(parents=True, exist_ok=True)
    g = OpenGuard(f"ns1e-fuse-{k:03d}", reads, [sd / "fusion", sd / "freeze"])
    pg = no_process(light=True)
    try:
        with g, pg:
            verify_plan_freeze(sd)
            verify_record_hashes(sd, "freeze/geometry-freeze.json")
            verify_record_hashes(sd, "freeze/identity-freeze.json")
            cfz, ofz = read_json(sd / "freeze/correspondence-freeze.json"), read_json(sd / "freeze/observation-freeze.json")
            prod_rel, rgb_rel = "correspondence/oracle-correspondences.npz", f"{SP.OBS_ACQ}/rgb-observation.npz"
            if sha256(sd / prod_rel) != cfz["files"][prod_rel] or sha256(sd / rgb_rel) != ofz["files"][rgb_rel]:
                raise SystemExit(f"{PREFIX} STOP the correspondence product / RGB observation changed")
            if sha256(res(mrec["path"], run)) != mrec["sha256"]:
                raise SystemExit(f"{PREFIX} STOP the target map changed since the scene checkpoint")
            prod = load_npz(sd / prod_rel)
            r_ = read_members(sd / "geometry/epipolar-result.npz", ("P_epi", "valid_epi"))
            idn = load_npz(sd / "segmentation/local-identity.npz")
            rgb_l = read_members(sd / rgb_rel, ("rgb_L",))["rgb_L"]
            if not (np.array_equal(idn["left_core_row"], prod["left_core_row"])
                    and np.array_equal(idn["valid"], r_["valid_epi"])):
                raise SystemExit(f"{PREFIX} STOP identity, product and geometry are not aligned")
            uv = prod["uv_L"].astype(np.int64)
            rgb = rgb_l[uv[:, 1], uv[:, 0]].astype(np.float64) if len(uv) else np.zeros((0, 3), np.float64)
            patch = CORE.target_patch(r_["P_epi"], r_["valid_epi"], idn["temporary_entity_id"], rgb, target, k)
            sm = C2.load_map(res(mrec["path"], run))
            if patch["patch_id"] in sm.patch_ids:
                raise SystemExit(f"{PREFIX} STOP the patch id {patch['patch_id']} is already in the target map")
            fused, rec = B.fuse_h0(sm, patch, target)
            np.savez_compressed(sd / "fusion/target-patch.npz", xyz_h=patch["xyz_h"], rgb=patch["rgb"],
                                instance_id=patch["instance_id"])
            np.savez_compressed(sd / "fusion/fused-target-map.npz", **B.map_arrays(fused))
            fm = load_npz(sd / "fusion/fused-target-map.npz")
            if not (np.all(fm["instance_id"] == target) and all(str(p).startswith(("nb1c_gaze_", "ns1b_action_",
                                                                                   "ns1c_step_", "ns1c2_step_",
                                                                                   "ns1e_step_"))
                                                                for p in fm["patch_ids"])):
                raise SystemExit(f"{PREFIX} STOP the fused map holds a foreign id or patch")
            idsum = read_json(sd / "segmentation/identity-summary.json")
            out = {"schema": "NS1e-fusion-v1", "truth": SP.TRUTH_DERIVED, "code": cs, "global_step": k,
                   "statement": "the selected target's points of the frozen spherical measurement, fused into ONLY that "
                                "target's H0 map with the accepted surface map (12 mm / 12 mm) in canonical H0, with one "
                                "exact replay; incidental ids in view are never fused (they enter the memory only)",
                   "target": target, "patch_id": patch["patch_id"], "map_before_path": mrec["path"],
                   "map_before_sha256": mrec["sha256"], "valid_correspondences":
                       int(np.asarray(r_["valid_epi"], bool).sum()), "entities_in_view": idsum["entities"],
                   "incidental_ids_not_fused": sorted(int(e) for e in idsum["entities"] if int(e) != target),
                   "local_gaze_deg": d["action"]["local_gaze_deg"], "world_gaze_deg": d["action"]["world_gaze_deg"],
                   **rec}
            write_json(sd / "fusion/fusion.json", CORE.jsonable(out))
            write_json(sd / "freeze/fusion-freeze.json", {
                "schema": "NS1e-fusion-freeze-v1", "truth": SP.TRUTH_DERIVED, "frozen_utc": utc(), "code": cs,
                "global_step": k, "statement": "the target-only H0 fusion, frozen before the memory append",
                "files": {f: sha256(sd / f) for f in SP.FUSION_FILES}})
    finally:
        write_json(sd / "fusion/fusion-opened-files.json", guard_record(g, pg))
    return {kk: out[kk] for kk in ("action", "target", "map_before", "measured_points", "matched", "new", "map_after")}


# ------------------------------------------------------------------ the all-instance memory append (section 16)
def memory(ctx: Ctx) -> dict:
    run, sd, k = ctx.run, ctx.sd(), int(ctx.step)
    d = require_action(ctx, "memory")
    need(sd / "freeze/fusion-freeze.json", "fuse")
    once(sd / "memory", f"the memory event of step {k}")
    cs = require_committed(ctx, "memory")
    import ns1d_core as K
    import ns1e_core as CORE
    t = int(d["action"]["target"])
    prel = prev_state_rel(run, k)
    prev = read_json(run / prel)
    reads = ([run / prel, sd / "plan/decision.json", sd / "plan/planned-calibration.json", sd / "freeze/plan-freeze.json", sd / "freeze/observation-freeze.json",
              sd / "freeze/correspondence-freeze.json", sd / "freeze/geometry-freeze.json",
              sd / "freeze/identity-freeze.json", sd / "freeze/fusion-freeze.json"]
             + [sd / f for f in SP.SEG_FILES + SP.FUSION_FILES]
             + [sd / "correspondence/oracle-correspondences.npz", sd / "geometry/epipolar-result.npz"]
             + memory_reads(prev["memory"]["events"], run)
             + freeze_reads(sd, ("freeze/correspondence-freeze.json", "freeze/geometry-freeze.json",
                                 "freeze/identity-freeze.json", "freeze/fusion-freeze.json")))
    (sd / "memory").mkdir(parents=True, exist_ok=True)
    g = OpenGuard(f"ns1e-memory-{k:03d}", reads, [sd / "memory", sd / "freeze"])
    pg = no_process(light=True)
    try:
        with g, pg:
            verify_plan_freeze(sd)
            for fz in ("freeze/correspondence-freeze.json", "freeze/geometry-freeze.json", "freeze/identity-freeze.json",
                       "freeze/fusion-freeze.json"):
                verify_record_hashes(sd, fz)
            ledger, events = ledger_from(prev, run)
            require_memory_digest(ledger, prev["memory"]["digest"], f"the checkpoint before step {k}")
            e = len(events)
            if e != int(d["action"]["memory_event"]) or e != SP.memory_event_of_step(k):
                raise SystemExit(f"{PREFIX} STOP memory event {e} is not the planned event of step {k}")
            prod = load_npz(sd / "correspondence/oracle-correspondences.npz")
            geom = load_npz(sd / "geometry/epipolar-result.npz")
            ident = load_npz(sd / "segmentation/local-identity.npz")
            patch, info = K.memory_patch(prod, geom, ident)
            tp = load_npz(sd / "fusion/target-patch.npz")
            subset = K.target_subset_equal(patch, prod, tp["xyz_h"], ident["temporary_entity_id"], geom["valid_epi"], t)
            idsum = read_json(sd / "segmentation/identity-summary.json")
            if not subset or info["by_observed_id"] != idsum["entities"]:
                raise SystemExit(f"{PREFIX} STOP the memory patch is not the frozen measurement (subset {subset})")
            key = sha256(sd / "freeze/observation-freeze.json")
            before = {str(i): int(ledger.measured_points.get(int(i), 0)) for i in prev["scene_ids"]}
            adds = ledger.append(e, key, patch, t)
            np.savez_compressed(sd / "memory/memory-patch.npz", **patch)
            summ = ledger.summary()
            coherent = set(int(i) for i in prev["scene_ids"])
            row = {"event": e, "source": "ns1e", "global_step": k, "origin": f"NS1e step {k}", "target": t,
                   "observation_key": key, "patch": f"run:{SP.step_dir(k)}/memory/memory-patch.npz",
                   "patch_sha256": sha256(sd / "memory/memory-patch.npz"),
                   "additions": {str(kk): int(vv) for kk, vv in sorted(adds.items())}}
            rec = {"schema": "NS1e-memory-event-v1", "truth": SP.TRUTH_DERIVED, "code": cs,
                   "statement": "the step's ONE all-instance memory patch (accepted ns1d_core.memory_patch from the frozen "
                                "correspondence, geometry and identity), appended once to the accepted "
                                "InstanceMeasurementMemory with source_active_target_id = the active target",
                   "memory_event": e, "global_step": k, "event_minus_step": e - k, "active_target": t,
                   "observation_key": key, "row": row, "patch_info": info,
                   "own_target_additions": int(adds.get(t, 0)),
                   "coherent_cross_target_additions": {str(kk): int(vv) for kk, vv in sorted(adds.items())
                                                       if kk != t and kk in coherent},
                   "non_scheduler_additions": {str(kk): int(vv) for kk, vv in sorted(adds.items()) if kk not in coherent},
                   "measured_points_before": before,
                   "measured_points_after": {str(i): int(ledger.measured_points.get(int(i), 0)) for i in prev["scene_ids"]},
                   "target_subset_equals_fusion_patch": subset, "summary_after": summ,
                   "digest_after": CORE.ledger_digest(summ)}
            write_json(sd / "memory/event.json", CORE.jsonable(rec))
            write_json(sd / "freeze/memory-event-freeze.json", {
                "schema": "NS1e-memory-event-freeze-v1", "truth": SP.TRUTH_DERIVED, "frozen_utc": utc(), "code": cs,
                "global_step": k, "memory_event": e, "statement": "the memory append, frozen before the own-look context "
                                                                "update and the scene commit",
                "files": {f: sha256(sd / f) for f in SP.MEMORY_FILES}})
    finally:
        write_json(sd / "memory/memory-opened-files.json", guard_record(g, pg))
    return {"event": e, "own": rec["own_target_additions"], "cross": rec["coherent_cross_target_additions"],
            "non_scheduler": sum(rec["non_scheduler_additions"].values())}


# ------------------------------------------------------------------ update: own-look context, commit, refresh, checkpoint
STEP_FREEZES = ("freeze/plan-freeze.json", "freeze/observation-freeze.json", "freeze/correspondence-freeze.json",
                "freeze/geometry-freeze.json", "freeze/identity-freeze.json", "freeze/fusion-freeze.json",
                "freeze/memory-event-freeze.json")


def update(ctx: Ctx) -> dict:
    run, sd, k = ctx.run, ctx.sd(), int(ctx.step)
    d = require_action(ctx, "update")
    need(sd / "freeze/memory-event-freeze.json", "memory")
    once(sd / "update", f"the update of step {k}")
    cs = require_committed(ctx, "update")
    import ns1b_chart as CH
    import ns1b_core as B
    import ns1c2_core as C2
    import ns1c2_phase as PH
    import ns1e_core as CORE
    from fov3d.control import integrated as ic
    CH.ensure_policy_modules()
    import ns1a_core  # noqa: F401
    import fsg6f_frontier  # noqa: F401
    prel, pfz = prev_state_rel(run, k), prev_freeze_rel(run, k)
    prev = read_json(run / prel)
    t = int(d["action"]["target"])
    rec_t = prev["entities"][str(t)]
    mev = read_json(sd / "memory/event.json")
    obs = [f"{SP.OBS_ACQ}/calibration.json", f"{SP.OBS_ACQ}/rgb-observation.npz", f"{SP.OBS_AID}/reference-observation.npz"]
    reads = (record_reads(prev["entities"], run) + memory_reads(prev["memory"]["events"], run)
             + [run / f for f in read_json(run / pfz)["files"]]
             + [run / prel, run / pfz, run / "handoff/charts.json", sd / "plan/decision.json", sd / "plan/planned-calibration.json", sd / "freeze/plan-freeze.json",
                sd / "freeze/observation-freeze.json", sd / "freeze/fusion-freeze.json",
                sd / "freeze/memory-event-freeze.json"] + [sd / f for f in SP.FUSION_FILES + SP.MEMORY_FILES]
             + [sd / f for f in obs]
             + freeze_reads(sd, ("freeze/fusion-freeze.json", "freeze/memory-event-freeze.json"))
             + [sd / f for f in STEP_FREEZES])
    (sd / "update/probes").mkdir(parents=True, exist_ok=True)
    g = OpenGuard(f"ns1e-update-{k:03d}", reads, [sd / "update", run / "scene", run / "freeze"])
    pg = no_process()
    try:
        with g, pg, PH.GateGuard(d["phase_after_decide"], f"update step {k}") as gg:
            verify_record_hashes(run, pfz)
            verify_plan_freeze(sd)
            verify_record_hashes(sd, "freeze/fusion-freeze.json")
            g.mark("fusion_freeze_verified")
            verify_record_hashes(sd, "freeze/memory-event-freeze.json")
            ledger, events = ledger_from(prev, run, [mev["row"]])
            require_memory_digest(ledger, mev["digest_after"], f"the memory event of step {k}")
            if len(events) - 1 != int(mev["memory_event"]) or int(mev["global_step"]) != k:
                raise SystemExit(f"{PREFIX} STOP the memory event / global step mapping of step {k} is inconsistent")
            g.mark("memory_event_verified")
            step_freezes = {f: sha256(sd / f) for f in STEP_FREEZES}
            fz = read_json(sd / "freeze/observation-freeze.json")
            for rel in obs:
                if sha256(sd / rel) != fz["files"][rel]:
                    raise SystemExit(f"{PREFIX} STOP {rel} changed after the observation freeze")
            chs = read_json(run / "handoff/charts.json")["charts"]
            r = np.asarray(chs[str(t)]["R_HC"], np.float64)
            fu = read_json(sd / "fusion/fusion.json")
            # -- (8) the active target's own-look context (Controller-01 observe order; the inherited oracle matcher)
            cal1 = read_json(sd / obs[0])
            rec1, meta1, st1 = B.matcher_state(cal1, load_npz(sd / obs[1]), load_npz(sd / obs[2]))
            state_file(sd / "update/controller-state.npz", st1, rec1["valid"])
            c_ctx = CORE.context_from_record(rec_t, run)
            ad = B.add_look(c_ctx, cal1, st1, rec1["valid"], r, tuple(d["action"]["local_gaze_deg"]))
            ev = B.evidence_arrays(c_ctx)
            np.savez_compressed(sd / "update/evidence.npz", **ev)
            planar = int((np.asarray(rec1["valid"], bool) & (np.asarray(rec1["instance_id"]) == t)).sum())
            new = json.loads(json.dumps(rec_t))
            new["looks"].append({"source": f"NS1e step {k:03d} ({SP.patch_id(k)})",
                                 "calibration": f"run:{SP.step_dir(k)}/{obs[0]}", "calibration_sha256": sha256(sd / obs[0]),
                                 "state": f"run:{SP.step_dir(k)}/update/controller-state.npz",
                                 "state_sha256": sha256(sd / "update/controller-state.npz"),
                                 "local_gaze": list(d["action"]["local_gaze_deg"])})
            new["visited"] = [list(v) for v in c_ctx.visited]
            new["current_local_gaze"] = list(c_ctx.gaze)
            new["own_looks"] = int(rec_t["own_looks"]) + 1
            new["evidence"] = {"path": f"run:{SP.step_dir(k)}/update/evidence.npz",
                               "sha256": sha256(sd / "update/evidence.npz")}
            if fu["action"] == "FUSED":
                fm = load_npz(sd / "fusion/fused-target-map.npz")
                new["map"] = {"path": f"run:{SP.step_dir(k)}/fusion/fused-target-map.npz",
                              "sha256": sha256(sd / "fusion/fused-target-map.npz"), "surfels": int(len(fm["xyz_h"])),
                              "patch_ids": [str(x) for x in fm["patch_ids"]]}
            new["planar_support_last_look"] = planar
            if len(c_ctx.history) != new["own_looks"]:
                raise SystemExit(f"{PREFIX} STOP the context history does not match the own-look count")
            ents = {kk: json.loads(json.dumps(v)) for kk, v in prev["entities"].items()}
            ents[str(t)] = new
            g.mark("context_updated")
            # -- (9-11) the accepted Controller-02 commit: fixations, refresh under the new M2 revisions, events
            m = PH.SceneMachine.from_json(d["machine_after_decide"])
            plan = plan_from_json(d["plan"])
            written, outs = {}, {}

            def probe(i):
                rec = ents[str(i)]
                rev = CORE.revision_m2(rec, ledger)
                o = CORE.probe_m2(rec, chs[str(i)], run, ledger, f"NORMAL M2 re-probe of entity {i} (step {k})")
                pth = sd / f"update/probes/e{i:05d}.json"
                write_json(pth, probe_file_record(i, f"step-{k:03d}", rev, o, CORE.memory_counts(rec, ledger),
                                                  {"executed": False}))
                written[i] = {"path": f"run:{SP.step_dir(k)}/update/probes/e{i:05d}.json", "sha256": sha256(pth),
                              "revision": rev, "provenance": "fresh", "computed_at": f"step-{k:03d}"}
                outs[i] = o
                return C2.probe_result(o, i, {"probe_path": written[i]["path"], "revision": rev})
            outcome = ic.ObservationOutcome(initialized=None, record={
                "fusion": fu["action"], "map_before": fu["map_before"], "map_after": fu["map_after"],
                "measured_points": fu["measured_points"], "matched": fu["matched"], "new": fu["new"],
                "memory_event": int(mev["memory_event"]), "memory_additions": mev["row"]["additions"]})
            n_ev = len(m.events)
            g.mark("commit_begins")
            record = m.commit(plan, outcome, probe, lambda i: CORE.revision_m2(ents[str(i)], ledger))
            g.mark("refresh_complete")
            events_new = m.events[n_ev:]
            if t not in written:
                raise SystemExit(f"{PREFIX} STOP the target's revision did not change (no fresh probe)")
            problems = []
            for kk in ents:
                i = int(kk)
                rev = CORE.revision_m2(ents[kk], ledger)
                if i in written:
                    ents[kk]["probe"] = written[i]
                    ents[kk] = with_status(ents[kk], m.statuses[i], outs[i])
                else:
                    if list(rev) != list(prev["entities"][kk]["revision"]):
                        problems.append(f"entity {i}: revision changed without a fresh probe")
                    ents[kk]["probe"] = {**prev["entities"][kk]["probe"], "provenance": "cached"}
                    ents[kk] = with_status(ents[kk], m.statuses[i])
                ents[kk]["revision"] = rev
                ents[kk]["memory"] = CORE.memory_counts(ents[kk], ledger)
            if any(o["adapter"]["calls"]["P3"] for o in outs.values()):
                problems.append("P3 (the gate's predicted calibration) was called by a NORMAL probe")
            if gg.record()["normal_calls"]:
                problems.append("a final-look gate call in NORMAL")
            if problems:
                raise SystemExit(f"{PREFIX} STOP update step {k}: {problems} (Outcome 3)")
            reacts = []
            for e_ in events_new:
                if e_["event"] != "natural_reactivation":
                    continue
                b = int(e_["object"])
                pb, pa = prev["entities"][str(b)], ents[str(b)]
                reacts.append({"object": b, "triggering_target": int(e_["trigger_target"]), "global_step": k,
                               "memory_event": int(mev["memory_event"]),
                               "cross_target_points_added": int(mev["row"]["additions"].get(str(b), 0)),
                               "revision_before": pb["revision"], "revision_after": pa["revision"],
                               "effective_points_before": pb["memory"]["effective_points"],
                               "effective_points_after": pa["memory"]["effective_points"],
                               "probe_before": e_["probe_before"], "probe_after": e_["probe_after"],
                               "quiet_since_step": e_.get("quiet_since_step"), "next_proposal": pa.get("proposal"),
                               "state_after": e_["state_after"]})
            rank1 = None
            if t in SP.RANK1:
                rank1 = {"target": t, "global_step": k, "own_look": new["own_looks"], "source": d["action"]["source"],
                         "north_star_spherical_target_points": int(fu["measured_points"]),
                         "controller_state_target_support": planar, "fusion": fu["action"], "new_surfels": fu["new"],
                         "status_after": ents[str(t)]["status"]["label"]}
            summ = ledger.summary()
            scene = {"schema": "NS1e-scene-state-v1", "truth": SP.TRUTH_DERIVED, "label": f"after-step-{k:03d}",
                     "code": cs, "last_global_step": k, "next_global_step": k + 1, "phase": m.phase.value,
                     "current": t, "previous": prev["current"], "attention_bout": int(record["attention_bout"]),
                     "executed_actions_total": int(prev["executed_actions_total"]) + 1,
                     "new_actions": int(prev["new_actions"]) + 1, "budget": prev["budget"], "cap": prev["cap"],
                     "scene_ids": prev["scene_ids"], "ambiguous": prev["ambiguous"], "entities": ents,
                     "machine": m.to_json(), "memory": {"events": events, "summary": summ,
                                                        "digest": CORE.ledger_digest(summ),
                                                        "measured_points": {str(kk): int(vv) for kk, vv in
                                                                            sorted(ledger.measured_points.items())}},
                     "map_digest": CORE.map_digest(ents), "events": d.get("events_in_decide", []) + events_new,
                     "last_action": {"global_step": k, "kind": d["kind"], "phase": d["action"]["phase"], "target": t,
                                     "decision": d["action"]["decision"], "reason": d["scheduler_reason"],
                                     "source": d["action"]["source"], "local_gaze_deg": d["action"]["local_gaze_deg"],
                                     "world_gaze_deg": d["action"]["world_gaze_deg"], "fusion": fu["action"],
                                     "fusion_new": fu["new"], "fusion_matched": fu["matched"],
                                     "target_points": fu["measured_points"], "patch_id": fu["patch_id"],
                                     "memory_event": int(mev["memory_event"]), "memory_additions": mev["row"]["additions"],
                                     "transition": d.get("target_transition")},
                     "machine_action_record": CORE.jsonable({kk: v for kk, v in record.items()
                                                             if kk not in ("vergence", "focus")}),
                     "natural_reactivations": reacts, "rank1_look": rank1, "fresh_probes": sorted(written),
                     "table": scene_table(ents), "gate_guard": gg.record()}
            rel = SP.state_after(k)
            write_json(run / rel, CORE.jsonable(scene))
            upd = {"schema": "NS1e-update-v1", "truth": SP.TRUTH_DERIVED, "code": cs, "global_step": k, "target": t,
                   "statement": "(8) the active target's own-look context in Controller-01 observe order; (9) the "
                                "accepted SceneMachine.commit; (10) the refresh under the new M2 revisions (a fresh "
                                "probe wherever the revision changed, the cache elsewhere); (11) its events",
                   "order_marks": [e_["label"] for e_ in g.events if e_.get("event") == "mark"],
                   "matcher": CORE.jsonable(meta1), "controller_state_target_support": planar,
                   "controller_state_target_pixels_L": int((st1["ids_left"] == t).sum()),
                   "north_star_target_points": int(fu["measured_points"]), "evidence_adapter": ad,
                   "evidence_cells": {n: int(v.sum()) for n, v in ev.items()}, "own_looks": new["own_looks"],
                   "visited": new["visited"], "fresh_probes": sorted(written), "status_after": ents[str(t)]["status"],
                   "events": events_new, "natural_reactivations": reacts, "rank1_look": rank1,
                   "gate_guard": gg.record(), "scene_state": {"path": rel, "sha256": sha256(run / rel)}}
            write_json(sd / "update/update.json", CORE.jsonable(upd))
            step_files = sorted(str(p.relative_to(run)) for p in [sd / "update/update.json",
                                                                   sd / "update/controller-state.npz",
                                                                   sd / "update/evidence.npz"]
                                + [sd / f"update/probes/e{i:05d}.json" for i in sorted(written)])
            write_json(run / SP.checkpoint_rel(k), {
                "schema": "NS1e-checkpoint-v1", "truth": SP.TRUTH_DERIVED, "frozen_utc": utc(), "code": cs,
                "global_step": k, "memory_event": int(mev["memory_event"]),
                "statement": "the scene checkpoint after step k: a restart resumes from here",
                "files": {f: sha256(run / f) for f in [rel] + step_files},
                "step_freezes": step_freezes})
    finally:
        write_json(sd / "update/update-opened-files.json", guard_record(g, pg))
    return {"target": t, "status_after": ents[str(t)]["status"]["label"], "proposal": ents[str(t)].get("proposal"),
            "fresh": sorted(written), "events": [[e_["event"], e_["object"]] for e_ in events_new],
            "phase": m.phase.value}


# ------------------------------------------------------------------ the drivers
def stage_cmd(ctx: Ctx, stage: str, step: int | None) -> list[str]:
    cmd = [sys.executable, str(HERE / "ns1e_run.py"), stage, "--run", str(ctx.run)]
    if step is not None:
        cmd += ["--step", str(step)]
    if ctx.dev:
        cmd.append("--dev")
    if stage in SP.RENDER_STAGES and ctx.rehearsal_spp is not None:
        cmd += ["--rehearsal-spp", str(int(ctx.rehearsal_spp))]
    return cmd


def run_stage(ctx: Ctx, stage: str, step: int | None) -> None:
    p = subprocess.run(stage_cmd(ctx, stage, step), cwd=REPO)
    if p.returncode != 0:
        raise SystemExit(f"{PREFIX} STOP stage {stage}{'' if step is None else f' of step {step}'} exited {p.returncode}")


def loop(ctx: Ctx, max_steps: int | None = None) -> dict:
    import ns1e_core as CORE
    run = ctx.run
    require_handoff(run)
    need(run / "gate-harness/gate-harness.json", "gate-harness")
    if (run / "freeze/control-freeze.json").exists():
        raise Refused(f"{PREFIX} REFUSED the control loop is frozen")
    require_committed(ctx, "loop")
    t0 = time.time()
    st0 = read_json(run / SP.scene_state_rel("initial"))
    k = int(st0["next_global_step"])
    while (run / SP.checkpoint_rel(k)).exists():
        k += 1
    steps = []
    (run / "loop").mkdir(parents=True, exist_ok=True)
    while True:
        if (run / "scene/terminal.json").exists():
            if not (run / "freeze/control-freeze.json").exists():
                run_stage(ctx, "freeze-control", None)
            break
        if max_steps is not None and len(steps) >= max_steps:
            break
        sd = run / SP.step_dir(k)
        try:
            cls = CORE.classify_step(sd)
        except CORE.StepAmbiguous as exc:
            raise SystemExit(f"{PREFIX} STOP an ambiguous step directory: {exc}")
        if cls["exists"]:
            write_json(run / f"loop/partial-step-{k:03d}.json", {"step": k, "classification": cls, "utc": utc(),
                                                                 "statement": "STOP: a partial / ambiguous action; "
                                                                              "never guessed, never resumed silently"})
            raise SystemExit(f"{PREFIX} STOP step {k} is partial: completed {cls['stages_done']}; next "
                             f"{cls['next_stage']} (report; do not guess)")
        ts = time.time()
        timing = {}
        for stage in SP.STEP:
            t_s = time.time()
            run_stage(ctx, stage, k)
            timing[stage] = round(time.time() - t_s, 2)
            if stage == "schedule":
                d = read_json(sd / "plan/decision.json")
                if d["kind"] not in ("attend", "final_residue"):
                    break
        d = read_json(sd / "plan/decision.json")
        row = {"step": k, "kind": d["kind"], "seconds": round(time.time() - ts, 1), "stage_seconds": timing,
               "utc": utc()}
        if d["kind"] in ("attend", "final_residue"):
            sc = read_json(run / SP.state_after(k))
            row.update({"target": d["action"]["target"], "reason": d["scheduler_reason"], "phase": d["action"]["phase"],
                        "source": d["action"]["source"], "local": d["action"]["local_gaze_deg"],
                        "status_after": sc["entities"][str(d["action"]["target"])]["status"]["label"],
                        "events": [[e["event"], e["object"]] for e in sc["events"]], "new_actions": sc["new_actions"]})
            print(f"{PREFIX} step {k}: {d['action']['target']} {d['scheduler_reason']} {d['action']['source']} "
                  f"{d['action']['local_gaze_deg']} -> {row['status_after']} ({row['seconds']} s) "
                  f"events {row['events']}", flush=True)
        else:
            print(f"{PREFIX} step {k}: terminal {d['kind']}", flush=True)
        steps.append(row)
        with open(run / "loop/progress.jsonl", "a") as f:
            f.write(json.dumps(row, sort_keys=True) + "\n")
        k += 1
    return {"steps": len(steps), "seconds": round(time.time() - t0, 1),
            "terminal": (run / "scene/terminal.json").exists(), "control_frozen": (run / "freeze/control-freeze.json").exists()}


# ------------------------------------------------------------------ freeze-control (the end of all control operation)
def control_files(run: Path) -> list[str]:
    skip_top = {"manifest.json", "check-summary.json", "process-log.jsonl"}
    out = []
    for p in sorted(run.rglob("*")):
        if not p.is_file():
            continue
        rel = str(p.relative_to(run))
        if rel in skip_top or rel.startswith(("evaluation/", "control/")) or rel == "freeze/control-freeze.json":
            continue
        out.append(rel)
    return out


def freeze_control(ctx: Ctx) -> dict:
    import ns1e_core as CORE
    run = ctx.run
    need(run / "scene/terminal.json", "the terminal record")
    once(run / "control/control-manifest.json", "the control manifest")
    cs = require_committed(ctx, "freeze-control")
    files = control_files(run)
    term = read_json(run / "scene/terminal.json")
    k = int(term["global_step"])
    last = SP.state_after(k - 1) if (run / SP.state_after(k - 1)).exists() else SP.scene_state_rel("initial")
    g = OpenGuard("ns1e-freeze-control", [run / f for f in files], [run / "control", run / "freeze"])
    pg = no_process()
    try:
        with g, pg:
            hashes = {f: sha256(run / f) for f in files}
            final = read_json(run / last)
            out = {"schema": "NS1e-control-manifest-v1", "truth": SP.TRUTH_DERIVED, "code": cs,
                   "control_complete": term["kind"] == "closed", "control_incomplete_cap": term["kind"] == "cap",
                   "terminal_kind": term["kind"], "terminal_global_step": k, "final_scene_state": last,
                   "final_scene_state_sha256": hashes[last], "new_actions": int(final["new_actions"]),
                   "executed_actions_total": int(final["executed_actions_total"]),
                   "outcome": term.get("outcome"), "terminal_breakdown": term.get("terminal_breakdown"),
                   "statement": "all controller operation is over; from here only the separate post-control evaluation "
                                "may open reference truth, and it has no path back into the controller",
                   "files": len(files)}
            write_json(run / "control/control-manifest.json", CORE.jsonable(out))
            write_json(run / "freeze/control-freeze.json", {
                "schema": "NS1e-control-freeze-v1", "truth": SP.TRUTH_DERIVED, "frozen_utc": utc(), "code": cs,
                "control_manifest_sha256": sha256(run / "control/control-manifest.json"),
                "statement": "every control file, frozen before any reference truth is opened", "files": hashes})
    finally:
        write_json(run / "control/control-freeze-opened-files.json", guard_record(g, pg))
    return {"kind": term["kind"], "new_actions": out["new_actions"], "files": len(files)}


# ------------------------------------------------------------------ evaluate (post-control; separate process; section 26)
def evaluate(ctx: Ctx) -> dict:
    import ns1e_core as CORE
    run = ctx.run
    need(run / "freeze/control-freeze.json", "freeze-control")
    cm = read_json(run / "control/control-manifest.json")
    if not (cm.get("control_complete") is True or cm.get("control_incomplete_cap") is True):
        raise Refused(f"{PREFIX} REFUSED the control manifest says neither complete nor cap")
    once(run / "evaluation/evaluation.json", "the post-control evaluation")
    cs = require_committed(ctx, "evaluate")
    import breadth1_glance as BG1          # accepted Breadth-1 extraction / orientation test (read-only)
    import breadth1_spec as B1S            # accepted exact cell weights
    import classroom_oracle1_eval as EV    # accepted exact 12-mm spatial-hash coverage
    from fov3d.reconstruction.measurement_memory import effective_target_geometry
    final = read_json(run / cm["final_scene_state"])
    ents = final["entities"]
    exr = SP.B1_RUN / SP.B1_EXR
    cal_ref = ents["172"]["looks"][0]["calibration"]
    reads = ([run / "control/control-manifest.json", run / "freeze/control-freeze.json", run / cm["final_scene_state"],
              exr, res(cal_ref, run)] + [res(e["map"]["path"], run) for e in ents.values()]
             + memory_reads(final["memory"]["events"], run))
    (run / "evaluation").mkdir(parents=True, exist_ok=True)
    g = OpenGuard("ns1e-evaluate", reads, [run / "evaluation"])
    pg = no_process()
    try:
        with g, pg:
            cfz = read_json(run / "freeze/control-freeze.json")
            if sha256(run / "control/control-manifest.json") != cfz["control_manifest_sha256"] or \
                    sha256(run / cm["final_scene_state"]) != cfz["files"][cm["final_scene_state"]]:
                raise SystemExit(f"{PREFIX} STOP the control freeze does not verify")
            for e in ents.values():
                ref = e["map"]["path"]
                if sha256(res(ref, run)) != e["map"]["sha256"]:
                    raise SystemExit(f"{PREFIX} STOP a final map differs from the frozen record")
            ledger, _ev = ledger_from(final, run)
            require_memory_digest(ledger, final["memory"]["digest"], "the final checkpoint")
            g.mark("control_freeze_verified")
            g.mark("reference_access_begins")
            if sha256(exr) != SP.B1_EXR_SHA256:
                raise SystemExit(f"{PREFIX} STOP the Breadth-1 reference EXR is not the accepted one")
            ex = BG1.extract_exr(exr)
            inst, pos = ex["instance"], ex["position_w"]
            if inst.shape != (SP.B1_HEIGHT, SP.B1_WIDTH) or not ex["index_integral"]:
                raise SystemExit(f"{PREFIX} STOP the reference raster is not 720 x 360 with an integral Object Index")
            cal = read_json(res(cal_ref, run))
            hr, ho = head_pose(cal)
            orient = BG1.orientation_residuals(pos, inst > 0, hr, ho)
            if orient["outside"]:
                raise SystemExit(f"{PREFIX} STOP the reference is not in the North-Star head frame: {orient}")
            w = B1S.row_weights()
            sphere = float(w.sum() * SP.B1_WIDTH)
            rows, arrays = {}, {}
            tot = {"cells": 0, "covered": 0, "omega": 0.0, "omega_cov": 0.0, "covered_eff": 0, "omega_cov_eff": 0.0}
            for kk in sorted(ents, key=int):
                i = int(kk)
                mask = CORE.reference_mask(inst, pos, i)
                ncell = int(mask.sum())
                surf = CORE.map_xyz(ents[kk], run)
                surf = surf[np.isfinite(surf).all(axis=1)]
                eff = effective_target_geometry(surf, ledger.snapshot(i).xyz_h)
                row = {"temporary_entity_id": i, "reference_cells": ncell, "final_persistent_surfels": int(len(surf)),
                       "effective_points": int(len(eff)), "own_looks": int(ents[kk]["own_looks"]),
                       "terminal_state": ents[kk]["status"]["label"]}
                if ncell == 0:
                    row.update({"status": SP.NO_REFERENCE, "reference_solid_angle_sr": 0.0, "covered_cells": None,
                                "uncovered_cells": None, "coverage_fraction": None, "coverage_fraction_weighted": None,
                                "effective_coverage_fraction": None, "effective_coverage_fraction_weighted": None})
                    rows[kk] = row
                    continue
                ref = CORE.head_points(pos[mask], hr, ho)
                cov = EV._covered(ref, surf, SP.COVERAGE_RADIUS_M)
                cov_e = EV._covered(ref, eff, SP.COVERAGE_RADIUS_M)
                rr, cc = np.nonzero(mask)
                cmask = np.zeros_like(mask)
                cmask[rr[cov], cc[cov]] = True
                emask = np.zeros_like(mask)
                emask[rr[cov_e], cc[cov_e]] = True
                om, om_c, om_e = CORE.weighted(mask, w), CORE.weighted(cmask, w), CORE.weighted(emask, w)
                row.update({"status": "EVALUATED", "reference_solid_angle_sr": om, "covered_cells": int(cov.sum()),
                            "uncovered_cells": int((~cov).sum()), "coverage_fraction": float(cov.mean()),
                            "covered_solid_angle_sr": om_c, "coverage_fraction_weighted": om_c / om,
                            "effective_covered_cells": int(cov_e.sum()),
                            "effective_coverage_fraction": float(cov_e.mean()),
                            "effective_coverage_fraction_weighted": om_e / om})
                rows[kk] = row
                arrays[f"e{i:05d}_cells"] = np.stack([rr, cc], 1).astype(np.int32)
                arrays[f"e{i:05d}_covered"] = cov
                arrays[f"e{i:05d}_covered_effective"] = cov_e
                tot["cells"] += ncell
                tot["covered"] += int(cov.sum())
                tot["omega"] += om
                tot["omega_cov"] += om_c
                tot["covered_eff"] += int(cov_e.sum())
                tot["omega_cov_eff"] += om_e
            np.savez_compressed(run / "evaluation/coverage.npz", **arrays)
            no_ref = [int(k_) for k_, r_ in rows.items() if r_["status"] == SP.NO_REFERENCE]
            out = {"schema": "NS1e-evaluation-v1", "truth": SP.TRUTH_REFERENCE, "code": cs, "label": SP.LABEL_REFERENCE,
                   "statement": "POST-CONTROL evaluation of the final PERSISTENT maps of the ten coherent entities against "
                                "the accepted Breadth-1 0.5-degree whole-sphere first-hit reference; covered iff within "
                                "12 mm (Euclidean) of a final persistent surfel. The effective-geometry numbers are a "
                                "labelled diagnostic, not persistent reconstruction",
                   "reference": {"path": str(exr), "sha256": SP.B1_EXR_SHA256, "raster": [SP.B1_WIDTH, SP.B1_HEIGHT],
                                 "cell_deg": 0.5, "sphere_solid_angle_sr": sphere,
                                 "orientation_check": orient, "head_pose_source": cal_ref,
                                 "identity": "the accepted _assign_instance_ids assignment (NS1a sealed catalog == the "
                                             "accepted Controller-01 catalog used by Breadth-1)"},
                   "radius_m": SP.COVERAGE_RADIUS_M, "coverage_function": "classroom_oracle1_eval._covered (accepted)",
                   "primary": "final persistent SurfaceMap only (memory excluded)", "per_entity": rows,
                   "no_reference_ids": no_ref,
                   "aggregate": {"reference_cells": tot["cells"], "covered_cells": tot["covered"],
                                 "micro_coverage": tot["covered"] / tot["cells"] if tot["cells"] else None,
                                 "reference_solid_angle_sr": tot["omega"], "covered_solid_angle_sr": tot["omega_cov"],
                                 "micro_coverage_weighted": tot["omega_cov"] / tot["omega"] if tot["omega"] else None},
                   "effective_geometry_diagnostic": {
                       "label": SP.LABEL_EFFECTIVE_DIAG, "covered_cells": tot["covered_eff"],
                       "micro_coverage": tot["covered_eff"] / tot["cells"] if tot["cells"] else None,
                       "micro_coverage_weighted": tot["omega_cov_eff"] / tot["omega"] if tot["omega"] else None},
                   "historical_reference": {**SP.HISTORICAL_98, "label": SP.LABEL_NON_COMPARABLE,
                                            "comparable": False,
                                            "statement": "NOT numerically comparable with NS1e: same 12-mm criterion, "
                                                         "different reference sampling (0.25-degree cyclopean vs 0.5-degree "
                                                         "whole sphere), object universe (25 localized vs 10 coherent) "
                                                         "and angular domain; no better / worse claim"},
                   "control": {"terminal_kind": cm["terminal_kind"], "new_actions": cm["new_actions"],
                               "outcome": cm.get("outcome")}}
            write_json(run / "evaluation/evaluation.json", CORE.jsonable(out))
    finally:
        write_json(run / "evaluation/evaluation-opened-files.json", guard_record(g, pg))
    return {"micro": out["aggregate"]["micro_coverage"], "weighted": out["aggregate"]["micro_coverage_weighted"],
            "effective": out["effective_geometry_diagnostic"]["micro_coverage"], "no_reference": no_ref}


# ------------------------------------------------------------------ visuals and manifest
def visualize(ctx: Ctx, vis: Path) -> dict:
    run = ctx.run
    need(run / "evaluation/evaluation.json", "evaluate")
    import ns1e_visuals as V
    man = V.visualize(run, vis)
    write_manifest(run)
    return {k: v["sha256"] for k, v in man["figures"].items()}


def write_manifest(run: Path) -> dict:
    files = sorted(str(p.relative_to(run)) for p in run.rglob("*") if p.is_file()
                   and p.name not in ("manifest.json", "check-summary.json", "process-log.jsonl"))
    m = {"schema": "NS1e-manifest-v1", "experiment": SP.EXPERIMENT, "contract": SP.CONTRACT, "code": code_state(),
         "base_commit": SP.BASE_COMMIT, "truth": TRUTH_CLASSES, "files": {f: sha256(run / f) for f in files}}
    write_json(run / "manifest.json", m)
    return m


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=SP.COMMANDS)
    ap.add_argument("--run", type=Path, default=SP.RUN_DEFAULT)
    ap.add_argument("--visuals", type=Path, default=None)
    ap.add_argument("--step", type=int, default=None)
    ap.add_argument("--dev", action="store_true", help="scratch development run only (never the canonical RUN)")
    ap.add_argument("--rehearsal-spp", type=int, default=None, help="loop / preflight / acquire --dev only")
    ap.add_argument("--max-steps", type=int, default=None, help="loop --dev only: stop a development loop early")
    a = ap.parse_args(argv)
    if (a.command in SP.STEP) != (a.step is not None):
        raise SystemExit(f"{PREFIX} --step is required by, and only by, the step stages")
    if a.rehearsal_spp is not None and (a.command not in ("loop",) + SP.RENDER_STAGES or not a.dev):
        raise SystemExit(f"{PREFIX} --rehearsal-spp is a `loop --dev` / render-stage --dev option only")
    if a.max_steps is not None and (a.command != "loop" or not a.dev):
        raise SystemExit(f"{PREFIX} --max-steps is a `loop --dev` option only")
    ctx = Ctx(a.run, a.dev, a.step, a.rehearsal_spp)
    t0 = time.time()
    fns = {"source": source, "synthetic": synthetic, "handoff": handoff, "gate-harness": gate_harness,
           "schedule": schedule, "preflight": preflight, "acquire": acquire, "freeze-observation": freeze_observation,
           "perfect-correspondence": perfect_correspondence, "freeze-correspondence": freeze_correspondence,
           "spherical-geometry": spherical_geometry, "freeze-geometry": freeze_geometry,
           "local-oracle-segmentation": local_oracle_segmentation, "freeze-identity": freeze_identity, "fuse": fuse,
           "memory": memory, "update": update, "loop": lambda c: loop(c, a.max_steps), "freeze-control": freeze_control,
           "evaluate": evaluate, "visualize": lambda c: visualize(c, a.visuals or SP.VIS_DEFAULT)}
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
    print(f"{PREFIX} {a.command}{'' if a.step is None else f' step {a.step}'} ok "
          + json.dumps(out, sort_keys=True, default=str)[:800], flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
