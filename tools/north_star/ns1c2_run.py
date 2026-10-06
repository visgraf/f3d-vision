"""North Star-1c2: correct Controller-02 NORMAL / RESIDUE semantics (run order, truth boundary, process contract).

Contract: docs/north-star/ns1c2-controller02-phase-semantics-contract.md.

    .venv/bin/python tools/north_star/ns1c2_run.py source         --run RUN
    .venv/bin/python tools/north_star/ns1c2_run.py synthetic      --run RUN
    .venv/bin/python tools/north_star/ns1c2_run.py known-answer   --run RUN
    .venv/bin/python tools/north_star/ns1c2_run.py eligibility    --run RUN
    .venv/bin/python tools/north_star/ns1c2_run.py charts         --run RUN
    .venv/bin/python tools/north_star/ns1c2_run.py contexts       --run RUN
    .venv/bin/python tools/north_star/ns1c2_run.py initial-probe  --run RUN
    .venv/bin/python tools/north_star/ns1c2_run.py prefix         --run RUN    # steps 0-3, replayed (no Blender)
    .venv/bin/python tools/north_star/ns1c2_run.py divergence     --run RUN    # frozen before any render
    .venv/bin/python tools/north_star/ns1c2_run.py loop           --run RUN    # steps >= 4
    .venv/bin/python tools/north_star/ns1c2_run.py visualize      --run RUN --visuals VIS

    step stages (normally launched by ``prefix`` / ``loop``), each once per global step k:
    prefix k = 0..3:  schedule | replay | fuse | update
    new    k >= 4:    schedule | preflight | acquire | freeze-observation | perfect-correspondence |
                      freeze-correspondence | spherical-geometry | freeze-geometry | local-oracle-segmentation | fuse |
                      update                                                                  --run RUN --step k

Every canonical stage runs once (per step for the step stages), from a clean pushed commit, under the accepted
``nb1a_guard.OpenGuard`` allowlist and, wherever policy code runs, under the NS1c2 gate guard (``final_look_gate_v1``
refused outside RESIDUE).  The prefix stages also run under the accepted ``NoProcessGuard`` (no process, so no Blender).
``--dev`` runs on a scratch development run (never the canonical RUN); ``eligibility --dev --dev-scene 172,10,110,178``
sets the rehearsal scene; ``loop --dev --rehearsal-spp N`` renders the factory-startup rehearsal instead of Classroom.
"""
from __future__ import annotations

import argparse
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

import ns1c2_spec as SP  # noqa: E402
from nb1a_guard import OpenGuard  # noqa: E402  (accepted, read-only)

PREFIX = "[ns1c2]"
TRUTH_CLASSES = {
    "ORACLE INPUT": "the saved NS1a initialization looks, the accepted NS1b look, NS1c's four measured prefix "
                    "observations (replayed read-only) and the new rendered observations; the ORACLE AID (Position, "
                    "Object Index) used by the perfect correspondence services and the local segmentation aid",
    "DERIVED": "the coherent seed set, the policy charts, the controller contexts, the NORMAL probes, the Controller-02 "
               "statuses, dispositions, phases and scheduler decisions, the world-gaze mappings, the truth-stripped "
               "correspondences, the spherical geometry, the local identity attachment, the H0 fusions and the scene "
               "states",
    "ACCEPTED HISTORICAL REFERENCE": "the accepted Controller-01 trajectories and Controller-02 events / final residue, "
                                     "used only by the known-answer stage",
    "REFERENCE / EVALUATION": "the sealed instance catalogs of the new observations (never opened by any NS1c2 stage)",
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
    def __init__(self, run: Path, dev: bool, step: int | None = None, dev_scene: list[int] | None = None,
                 rehearsal_spp: int | None = None) -> None:
        self.run, self.dev, self.step = run.resolve(), dev, step
        self.dev_scene, self.rehearsal_spp = dev_scene, rehearsal_spp
        if dev and self.run == SP.RUN_DEFAULT.resolve():
            raise SystemExit(f"{PREFIX} STOP --dev never runs on the canonical RUN")
        if (dev_scene is not None or rehearsal_spp is not None) and not dev:
            raise SystemExit(f"{PREFIX} STOP --dev-scene / --rehearsal-spp are development rehearsal options only")

    def p(self, rel: str) -> Path:
        return self.run / rel

    def sd(self) -> Path:
        if self.step is None:
            raise SystemExit(f"{PREFIX} STOP a step stage needs --step")
        return self.run / SP.step_dir(self.step)


def log_process(ctx: Ctx, command: str, t0: float, status: str, extra: dict | None = None) -> None:
    ctx.run.mkdir(parents=True, exist_ok=True)
    entry = {"command": command, "step": ctx.step, "argv": sys.argv, "executable": sys.executable,
             "code": code_state(), "dev": ctx.dev, "finished_utc": utc(), "seconds": round(time.time() - t0, 3),
             "status": status, **(extra or {})}
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


def guard_record(g: OpenGuard, extra: dict | None = None) -> dict:
    rec = g.record()
    rec["modules_loaded"] = {m: m in sys.modules for m in ("cv2", "fsg_stereo", "ab1a_stereo", "ab1d_match",
                                                           "ab1d3_sgbm", "ab1b_oracle", "fsg6f_frontier",
                                                           "fov3d.control.integrated", "fov3d.control.controller02")}
    rec["violations_count"] = len(rec["violations"])
    rec["forbidden_reads"] = sorted({e["path"] for e in rec["events"] if e.get("event") == "open" and forbidden(e["path"])})
    rec["history_reads"] = sorted({e["path"] for e in rec["events"] if e.get("event") == "open"
                                   and any(h in e["path"] for h in SP.HISTORY_DIRS)})
    rec.update(extra or {})
    return rec


def verify_record_hashes(base: Path, freeze_rel: str) -> dict:
    fz = read_json(base / freeze_rel)
    bad = {f: h for f, h in fz["files"].items() if sha256(base / f) != h}
    if bad:
        raise SystemExit(f"{PREFIX} STOP files changed after {freeze_rel}: {sorted(bad)[:5]}")
    return fz


def ns1a(rel: str) -> Path:
    return SP.NS1A_RUN / rel


def ns1b(rel: str) -> Path:
    return SP.NS1B_RUN / rel


def ns1c(rel: str) -> Path:
    return SP.NS1C_RUN / rel


def head_pose(c: dict) -> tuple[np.ndarray, np.ndarray]:
    return np.asarray(c["head_R_wh"], np.float64), np.asarray(c["head_origin_w_m"], np.float64)


def res(ref: str, run: Path) -> Path:
    import ns1c2_core as CORE
    return CORE.resolve(ref, run)


def ns1c_manifest() -> dict:
    if sha256(ns1c("manifest.json")) != SP.NS1C_MANIFEST_SHA256:
        raise SystemExit(f"{PREFIX} STOP the NS1c run manifest is not the pinned one")
    return read_json(ns1c("manifest.json"))


def ns1c_verify(rels, man: dict | None = None) -> dict:
    """Every NS1c file read must equal its NS1c manifest entry (the manifest is pinned)."""
    man = man if man is not None else ns1c_manifest()
    out, bad = {}, []
    for rel in rels:
        h = sha256(ns1c(rel))
        if man["files"].get(rel) != h:
            bad.append(rel)
        out[rel] = h
    if bad:
        raise SystemExit(f"{PREFIX} STOP NS1c files differ from the pinned NS1c manifest: {bad[:5]}")
    return out


# ------------------------------------------------------------------ source
def accepted_constants() -> dict:
    import fsg6f_public as PUB
    from fov3d.experiments.classroom_oracle import config as public, controller01 as c01, controller02 as x2
    from fov3d.reconstruction import association
    import tools.classroom_oracle1_epistemic  # noqa: F401
    got = {"SURFACE_FRONTIER": dict(PUB.SURFACE_FRONTIER), "FSG6F_FUSION": dict(PUB.FUSION),
           "FSG6F_OBJECT_ID": int(PUB.OBJECT_ID), "FSG6F_VERGENCE_M": float(PUB.VERGENCE_DISTANCE_M),
           "CYCLOPEAN_GRID_DEG": float(public.CYCLOPEAN_GRID_DEG),
           "MIN_INITIAL_TARGET_POINTS": int(public.MIN_INITIAL_TARGET_POINTS), "FUSION": dict(public.FUSION),
           "SURFACE_ASSOCIATION_RADIUS_M": float(association.SURFACE_ASSOCIATION_RADIUS_M),
           "ORDINARY_BUDGET": int(x2.BUDGET), "CONTROLLER01_WATCHDOG": int(c01.WATCHDOG),
           "MAX_OBJECT_FIXATIONS": int(public.MAX_OBJECT_FIXATIONS)}
    want = {"SURFACE_FRONTIER": SP.SURFACE_FRONTIER, "FSG6F_FUSION": SP.FSG6F_FUSION,
            "FSG6F_OBJECT_ID": SP.FSG6F_OBJECT_ID, "FSG6F_VERGENCE_M": SP.FSG6F_VERGENCE_M,
            "CYCLOPEAN_GRID_DEG": SP.CYCLOPEAN_GRID_DEG, "MIN_INITIAL_TARGET_POINTS": SP.MIN_POINTS,
            "FUSION": {"association_radius_m": SP.ASSOCIATION_RADIUS_M, "hash_cell_m": SP.HASH_CELL_M},
            "SURFACE_ASSOCIATION_RADIUS_M": SP.ASSOCIATION_RADIUS_M, "ORDINARY_BUDGET": SP.BUDGET_EXPECTED,
            "CONTROLLER01_WATCHDOG": SP.BUDGET_EXPECTED, "MAX_OBJECT_FIXATIONS": SP.BUDGET_EXPECTED}
    if got != want:
        raise SystemExit(f"{PREFIX} STOP the accepted constants differ: {got} != {want}")
    return got


def ns1c_decision_state() -> dict:
    """NS1c is NOT accepted and NOT merged: no ACCEPTED marker in any tracked document (acceptance markers are recorded
    in Markdown; checker code may name the marker only to forbid it); its report head is not an ancestor of the
    checked tree nor of main."""
    files = git("ls-files").split("\n")
    hits = [f for f in files if f.endswith(".md") and (REPO / f).is_file()
            and SP.NS1C_ACCEPTED_MARKER in (REPO / f).read_text(errors="replace")]
    anc = {ref: subprocess.run(["git", "merge-base", "--is-ancestor", SP.NS1C_REPORT_HEAD, ref], cwd=REPO).returncode == 0
           for ref in ("HEAD", "origin/main")}
    note = (REPO / "docs/north-star/ns1c-review-decision.md")
    return {"accepted_marker_files": hits, "ns1c_report_head_ancestor_of": anc,
            "review_decision_present": note.is_file()
            and "NS1c:  REVIEWED · NOT ACCEPTED · NOT MERGED" in note.read_text(),
            "ok": not hits and not any(anc.values()) and note.is_file()}


def source(ctx: Ctx) -> dict:
    run = ctx.run
    once(run / "source/source-manifest.json", "the source record")
    cs = require_committed(ctx, "source")
    origin = git("remote", "get-url", "origin")
    anc = {name: subprocess.run(["git", "merge-base", "--is-ancestor", sha, "HEAD"], cwd=REPO).returncode == 0
           for name, sha in (("base", SP.BASE_COMMIT), ("ns1b_acceptance", SP.NS1B_ACCEPTANCE),
                             ("ns1a_acceptance", SP.NS1A_ACCEPTANCE), ("contract", SP.CONTRACT_COMMIT))}
    contract_unchanged = subprocess.run(["git", "diff", "--quiet", SP.CONTRACT_COMMIT, "--", SP.CONTRACT],
                                        cwd=REPO).returncode == 0
    decision = ns1c_decision_state()
    if SP.CANONICAL_REMOTE not in origin or not all(anc.values()) or not contract_unchanged or not decision["ok"]:
        raise SystemExit(f"{PREFIX} STOP provenance: origin {origin}; ancestors {anc}; contract unchanged "
                         f"{contract_unchanged}; NS1c decision {decision}")
    import ns1b_chart as CH
    CH.ensure_policy_modules()
    consts = accepted_constants()
    prefix_rels = [f"{SP.step_dir(k)}/{rel}" for k, pins in SP.NS1C_PREFIX_PINS.items() for rel in pins]
    c01_files = sorted(glob.glob(str(SP.C01_RUN / SP.C01_TRAJECTORY_GLOB)))
    reads = ([ns1a(f) for f in SP.NS1A_PINS] + [ns1b(f) for f in SP.NS1B_PINS]
             + [ns1c("manifest.json"), ns1c("check-summary.json")] + [ns1c(r) for r in prefix_rels]
             + [ns1c(r) for r in SP.NS1C_SCENE_PINS] + [SP.C02_RUN / f for f in SP.C02_PINS] + c01_files)
    g = OpenGuard("ns1c2-source", reads, [run / "source"])
    try:
        with g:
            pins = {p: sha256(REPO / p) for p in SP.SOURCE_PINS}
            bad = {p: h for p, h in pins.items() if h != SP.SOURCE_PINS[p]}
            if bad:
                raise SystemExit(f"{PREFIX} STOP accepted sources changed: {bad}")
            a_pins = {rel: sha256(ns1a(rel)) for rel in SP.NS1A_PINS}
            b_pins = {rel: sha256(ns1b(rel)) for rel in SP.NS1B_PINS}
            bad = {**{f"ns1a:{k}": v for k, v in a_pins.items() if v != SP.NS1A_PINS[k]},
                   **{f"ns1b:{k}": v for k, v in b_pins.items() if v != SP.NS1B_PINS[k]}}
            if bad:
                raise SystemExit(f"{PREFIX} STOP the frozen NS1a / NS1b handoff changed: {bad}")
            man = ns1c_manifest()
            if sha256(ns1c("check-summary.json")) != SP.NS1C_CHECK_SUMMARY_SHA256:
                raise SystemExit(f"{PREFIX} STOP the NS1c check summary is not the pinned one")
            c_pins = ns1c_verify(prefix_rels + list(SP.NS1C_SCENE_PINS), man)
            badc = [r for r in prefix_rels if c_pins[r] != SP.NS1C_PREFIX_PINS[int(r.split("/")[1][-2:])][
                r.split("/", 2)[2]]] + [r for r in SP.NS1C_SCENE_PINS if c_pins[r] != SP.NS1C_SCENE_PINS[r]]
            if badc:
                raise SystemExit(f"{PREFIX} STOP the NS1c prefix pins differ: {badc[:5]}")
            c02 = {f: sha256(SP.C02_RUN / f) for f in SP.C02_PINS}
            lines = "".join(f"{Path(f).relative_to(SP.C01_RUN)} {sha256(f)}\n" for f in c01_files)
            c01_digest = hashlib.sha256(lines.encode()).hexdigest()
            if c02 != SP.C02_PINS or c01_digest != SP.C01_TRAJECTORY_DIGEST or len(c01_files) != SP.C01_TRAJECTORY_COUNT:
                raise SystemExit(f"{PREFIX} STOP the accepted Controller-01 / 02 history pins differ")
            summ = read_json(ns1b("check-summary.json"))
            if summ["marker"] != "NORTH_STAR1B_CHECKS_PASS" or summ["failed"]:
                raise SystemExit(f"{PREFIX} STOP the NS1b check summary does not pass")
            out = {"schema": "NS1c2-source-v1", "experiment": SP.EXPERIMENT, "code": cs, "origin": origin,
                   "ancestors": anc, "contract": SP.CONTRACT, "contract_commit": SP.CONTRACT_COMMIT,
                   "contract_unchanged": contract_unchanged, "base_commit": SP.BASE_COMMIT,
                   "ns1b_acceptance": SP.NS1B_ACCEPTANCE, "ns1a_acceptance": SP.NS1A_ACCEPTANCE,
                   "ns1c_diagnostic_source": {"implementation": SP.NS1C_IMPLEMENTATION, "report_head":
                                              SP.NS1C_REPORT_HEAD, "manifest_sha256": SP.NS1C_MANIFEST_SHA256,
                                              "check_summary_sha256": SP.NS1C_CHECK_SUMMARY_SHA256,
                                              "manifest_files": len(man["files"]), "prefix_pins": c_pins},
                   "ns1c_decision": decision, "source_pins": pins, "accepted_constants": consts,
                   "ordinary_budget": consts["ORDINARY_BUDGET"], "ns1a_handoff": a_pins, "ns1b_handoff": b_pins,
                   "ns1b_check_marker": summ["marker"], "ns1a_catalog_seal": SP.NS1A_CATALOG_SEAL,
                   "history": {"controller02": c02, "controller01_trajectories": len(c01_files),
                               "controller01_trajectory_digest": c01_digest, "literals": SP.HISTORICAL},
                   "adapter": "ns1b_chart.PolicyChartAdapter (accepted NS1b; P1-P3 unchanged)",
                   "scheduler": "fov3d.control.controller02.schedule_normal (accepted; unchanged)",
                   "phase_adapter": "tools/north_star/ns1c2_phase.SceneMachine (mirrors run_controller02)"}
            write_json(run / "source/source-manifest.json", out)
    finally:
        write_json(run / "source/source-opened-files.json", guard_record(g))
    return {"pins": len(pins), "ns1c_prefix_pins": len(prefix_rels), "budget": consts["ORDINARY_BUDGET"],
            "ns1c_not_accepted": decision["ok"]}


# ------------------------------------------------------------------ synthetic known answers
def synthetic(ctx: Ctx) -> dict:
    run = ctx.run
    need(run / "source/source-manifest.json", "source")
    once(run / "synthetic/synthetic-report.json", "the synthetic known answers")
    require_committed(ctx, "synthetic")
    import ns1c2_synthetic as SY
    rep = SY.run_all()
    write_json(run / "synthetic/synthetic-report.json", rep)
    if rep["failed"]:
        raise SystemExit(f"{PREFIX} STOP synthetic known answers failed: {rep['failed']}")
    return {"passed": rep["count"] - len(rep["failed"]), "count": rep["count"], "marker": rep["marker"]}


# ------------------------------------------------------------------ known answers on accepted data
def ns1b_172_record(run: Path) -> dict:
    """172's accepted NS1b post-action context as a record over the pinned NS1b files (no NS1c2 data)."""
    return {"temporary_entity_id": SP.CONTINUING, "initialization_rank": SP.NS1B_172["rank"],
            "looks": [{"calibration": f"ns1a:{SP.ns1a_obs(6, 'acquisition', 'calibration.json')}",
                       "state": "ns1b:context/controller-state.npz", "local_gaze": [0.0, 0.0]},
                      {"calibration": "ns1b:observation/acquisition/calibration.json",
                       "state": "ns1b:post/controller-state.npz", "local_gaze": list(SP.NS1B_172["gaze"])}],
            "visited": [list(v) for v in SP.NS1B_172["visited"]], "current_local_gaze": list(SP.NS1B_172["gaze"]),
            "own_looks": SP.NS1B_172["own_looks"], "evidence": {"path": "ns1b:post/evidence.npz"},
            "map": {"path": "ns1b:fusion/fused-target-map.npz", "surfels": SP.NS1B_172["map_surfels"]}}


def known_answer(ctx: Ctx) -> dict:
    run = ctx.run
    rep = read_json(run / "synthetic/synthetic-report.json") if (run / "synthetic/synthetic-report.json").exists() else {}
    if rep.get("failed") != []:
        raise Refused(f"{PREFIX} REFUSED the synthetic known answers must pass first")
    once(run / "known-answer/known-answer.json", "the known answers")
    cs = require_committed(ctx, "known-answer")
    import ns1b_chart as CH
    import ns1b_core as B
    import ns1c2_core as CORE
    import ns1c2_phase as PH
    import ns1c2_synthetic as SY
    from fov3d.control import controller02 as c2
    CH.ensure_policy_modules()
    import ns1a_core  # noqa: F401
    import fsg6f_frontier  # noqa: F401
    c01_files = sorted(glob.glob(str(SP.C01_RUN / SP.C01_TRAJECTORY_GLOB)))
    rec172 = ns1b_172_record(run)
    reads = c01_files + [SP.C02_RUN / f for f in SP.C02_PINS] + [
        ns1a(SP.ns1a_obs(6, "acquisition", "calibration.json")), ns1b("context/controller-state.npz"),
        ns1b("observation/acquisition/calibration.json"), ns1b("post/controller-state.npz"), ns1b("post/evidence.npz"),
        ns1b("fusion/fused-target-map.npz"), ns1b("post/post-action-probe.json"), ns1b("chart/policy-chart.json")]
    (run / "known-answer").mkdir(parents=True, exist_ok=True)
    g = OpenGuard("ns1c2-known-answer", reads, [run / "known-answer"])
    try:
        with g:
            lines = "".join(f"{Path(f).relative_to(SP.C01_RUN)} {sha256(f)}\n" for f in c01_files)
            if hashlib.sha256(lines.encode()).hexdigest() != SP.C01_TRAJECTORY_DIGEST or \
                    {f: sha256(SP.C02_RUN / f) for f in SP.C02_PINS} != SP.C02_PINS:
                raise SystemExit(f"{PREFIX} STOP the accepted history pins differ")
            traj = {int(Path(f).parent.name.split("_")[1]): read_json(f) for f in c01_files}
            events = read_json(SP.C02_RUN / "events.json")["events"]
            fres = read_json(SP.C02_RUN / "final-residue.json")
            with PH.GateGuard(c2.ScenePhase.NORMAL.value, "known-answer: historical trace") as gh:
                hist = SY.historical_trace(traj, events, fres, CORE.budget_live())
            h_ok, h_checks = SY.historical_ok(hist)
            # -- the residue-gate wiring harness: 172 at its accepted NS1b post-action state, DEFERRED at the budget
            for rel in ("context/controller-state.npz", "post/controller-state.npz", "post/evidence.npz",
                        "fusion/fused-target-map.npz", "observation/acquisition/calibration.json",
                        "post/post-action-probe.json", "chart/policy-chart.json"):
                if sha256(ns1b(rel)) != SP.NS1B_PINS[rel]:
                    raise SystemExit(f"{PREFIX} STOP the accepted NS1b file {rel} changed")
            ch = CORE.chart_record(SP.CONTINUING, 6, tuple(SP.NS1A_RANK_GAZES[5][1:]))
            nbc = read_json(ns1b("chart/policy-chart.json"))
            chart_ok = np.array_equal(np.asarray(ch["R_HC"]), np.asarray(nbc["R_HC"]))
            cal0 = read_json(ns1a(SP.ns1a_obs(6, "acquisition", "calibration.json")))
            hr, ho = head_pose(cal0)
            nbp = read_json(ns1b("post/post-action-probe.json"))["probe"]
            v, f = CORE.vergence_focus()
            m = PH.SceneMachine([SP.CONTINUING], budget=CORE.budget_live(), vergence=v, focus=f)
            outs = {}
            with PH.GateGuard(c2.ScenePhase.NORMAL.value, "known-answer: residue harness") as gr:
                def probe(i):
                    outs[i] = CORE.probe_entity(rec172, run, ch, "known-answer harness probe of 172")
                    return CORE.probe_result(outs[i], i)
                m.resume_initialized({SP.CONTINUING: CORE.budget_live()}, current=SP.CONTINUING, bout=1, step=0,
                                     probe=probe, revision=None)
                gate_detail = {}

                def final_gate(i, proposal):
                    gr.phase = m.phase.value
                    verdict, detail = CORE.residue_gate(rec172, run, ch, outs[i], proposal, hr, ho,
                                                        "known-answer residue gate of 172")
                    gate_detail.update(detail)
                    gr.phase = m.phase.value
                    return verdict
                status_before = m.statuses[SP.CONTINUING].label
                plan = m.decide(final_gate)
            pol = CORE.policy_comparison(nbp, outs[SP.CONTINUING])
            gd = B.compare(nbp["gate"]["detail"], gate_detail.get("detail"), 0.0, "gate/detail")
            harness = {"scene": [SP.CONTINUING], "status_before_decision": status_before,
                       "phase_at_gate": (m.gate_log[-1]["phase"] if m.gate_log else None),
                       "plan_kind": plan["kind"], "executed": False,
                       "verdict": {k: gate_detail.get(k) for k in ("admissible", "reason")},
                       "novel_service_count": ((gate_detail.get("detail") or {}).get("counts") or {}).get(
                           "novel_service_count"),
                       "accepted_ns1b_gate": {k: nbp["gate"][k] for k in ("admissible", "reason")},
                       "gate_detail_differences": gd[:5], "policy_differences_vs_ns1b": pol[:5],
                       "chart_equals_ns1b": chart_ok, "gate_guard": gr.record(), "phases": m.phases,
                       "statement": "a one-entity HARNESS scene (not the NS1c2 scene loop): 172 at its accepted NS1b "
                                    "post-action state with own fixations set to the budget, so DEFERRED; "
                                    "schedule_normal returns None; RESIDUE; the production residue gate path; the "
                                    "admitted proposal is NOT executed"}
            harness["ok"] = bool(status_before == "ACTIONABLE/DEFERRED:ordinary_budget"
                                 and harness["phase_at_gate"] == "RESIDUE" and plan["kind"] == "final_residue"
                                 and harness["verdict"] == {"admissible": True,
                                                            "reason": SP.NS1B_GATE_EXPECTED["reason"]}
                                 and harness["novel_service_count"] == SP.NS1B_GATE_EXPECTED["novel_service_count"]
                                 and not gd and not pol and chart_ok and gr.record()["normal_calls"] == 0
                                 and gr.record()["residue_calls"] == 1)
            out = {"schema": "NS1c2-known-answer-v1", "truth": SP.TRUTH_HISTORICAL, "code": cs,
                   "role": "ACCEPTED HISTORICAL REFERENCE and harness known answers (not NS1c2 scene measurements)",
                   "historical_controller02_trace": {**hist, "checks": h_checks, "ok": h_ok,
                                                     "gate_guard": gh.record(),
                                                     "input_files": {"controller01_trajectories": len(c01_files),
                                                                 "controller02": sorted(SP.C02_PINS)},
                                                     "literals": SP.HISTORICAL},
                   "residue_gate_harness": harness, "ok": bool(h_ok and harness["ok"])}
            write_json(run / "known-answer/known-answer.json", out)
    finally:
        write_json(run / "known-answer/known-answer-opened-files.json", guard_record(g))
    if not out["ok"]:
        raise SystemExit(f"{PREFIX} STOP known answers failed: historical {h_checks}; harness {harness['ok']}")
    return {"historical": h_ok, "harness": harness["ok"], "verdict": harness["verdict"]}


# ------------------------------------------------------------------ eligibility and charts (unchanged NS1c rules)
def eligibility(ctx: Ctx) -> dict:
    run = ctx.run
    ka = read_json(run / "known-answer/known-answer.json") if (run / "known-answer/known-answer.json").exists() else {}
    if not ka.get("ok"):
        raise Refused(f"{PREFIX} REFUSED the known answers must pass first")
    once(run / "eligibility/coherent-seed-set.json", "the coherent seed set")
    cs = require_committed(ctx, "eligibility")
    import ns1b_core as B
    import ns1c2_core as CORE
    reads = [ns1a(SP.NS1A_SEED_SET), ns1a("freeze/seed-set-freeze.json"), ns1a(SP.NS1A_GAZE_LIST)]
    g = OpenGuard("ns1c2-eligibility", reads, [run / "eligibility"])
    try:
        with g:
            for rel in (SP.NS1A_SEED_SET, SP.NS1A_GAZE_LIST, "freeze/seed-set-freeze.json"):
                if sha256(ns1a(rel)) != SP.NS1A_PINS[rel]:
                    raise SystemExit(f"{PREFIX} STOP NS1a {rel} changed")
            el = CORE.derive_coherent_set(read_json(ns1a(SP.NS1A_SEED_SET)))
            gazes = B.rank_gazes(read_json(ns1a(SP.NS1A_GAZE_LIST)))
            for row in el["coherent"] + el["deferred"]:
                row["initialization_gaze_deg"] = list(gazes[row["initialized_at_rank"]])
            match = (el["coherent_ids"] == list(SP.EXPECTED_COHERENT)
                     and el["deferred_ids"] == list(SP.EXPECTED_DEFERRED))
            out = {"schema": "NS1c2-eligibility-v1", "truth": SP.TRUTH_DERIVED, "code": cs,
                   "statement": "COHERENT_SEED_SET derived from the frozen NS1a seed set by the same single-patch rule "
                                "as NS1c; no name, catalog, semantic class or future visibility", **el,
                   "expected_from_mandate": {"coherent": list(SP.EXPECTED_COHERENT),
                                             "deferred": list(SP.EXPECTED_DEFERRED)},
                   "matches_expectation": match, "scene_ids": el["coherent_ids"]}
            if ctx.dev_scene is not None:
                rows = {r["temporary_entity_id"]: r for r in el["coherent"] + el["deferred"]}
                bad = [k for k in ctx.dev_scene if k not in rows]
                if bad or (set(ctx.dev_scene) & set(el["coherent_ids"])) - {SP.CONTINUING}:
                    raise SystemExit(f"{PREFIX} STOP the rehearsal scene may hold only 172 and non-coherent "
                                     f"initialized ids: {ctx.dev_scene}")
                out.update({"DEV_OVERRIDE": True, "scene_ids": sorted(ctx.dev_scene),
                            "scene_rows": [rows[k] for k in sorted(ctx.dev_scene)]})
            write_json(run / "eligibility/coherent-seed-set.json", out)
    finally:
        write_json(run / "eligibility/eligibility-opened-files.json", guard_record(g))
    if not out["matches_expectation"] and ctx.dev_scene is None:
        raise SystemExit(f"{PREFIX} STOP the derived set {el['coherent_ids']} / deferred {el['deferred_ids']} differs "
                         f"from the expected {list(SP.EXPECTED_COHERENT)} / {list(SP.EXPECTED_DEFERRED)}")
    return {"coherent": el["coherent_ids"], "deferred": el["deferred_ids"], "scene": out["scene_ids"]}


def scene_rows(elig: dict) -> list[dict]:
    return elig.get("scene_rows") or elig["coherent"]


def charts(ctx: Ctx) -> dict:
    run = ctx.run
    need(run / "eligibility/coherent-seed-set.json", "eligibility")
    once(run / "charts/policy-charts.json", "the policy charts")
    cs = require_committed(ctx, "charts")
    import ns1b_chart as CH
    import ns1c2_core as CORE
    g = OpenGuard("ns1c2-charts", [run / "eligibility/coherent-seed-set.json", ns1b("chart/policy-chart.json")],
                  [run / "charts"])
    try:
        with g:
            el = read_json(run / "eligibility/coherent-seed-set.json")
            out_rows, problems = {}, []
            for row in scene_rows(el):
                k = int(row["temporary_entity_id"])
                try:
                    ch = CORE.chart_record(k, row["initialized_at_rank"], tuple(row["initialization_gaze_deg"]))
                except CH.ChartSingular as exc:
                    problems.append(f"entity {k}: {exc}")
                    continue
                if not ch["checks"]["ok"] or ch["projected_baseline_norm"] < SP.CHART_SINGULAR_MIN:
                    problems.append(f"entity {k}: chart requirements fail {ch['checks']}")
                out_rows[str(k)] = ch
            nb = read_json(ns1b("chart/policy-chart.json"))
            c172 = out_rows.get(str(SP.CONTINUING))
            same172 = c172 is not None and np.array_equal(np.asarray(c172["R_HC"]), np.asarray(nb["R_HC"]))
            if c172 is not None and not same172:
                problems.append("C_172 differs from the accepted NS1b chart")
            out = {"schema": "NS1c2-charts-v1", "truth": SP.TRUTH_DERIVED, "code": cs, "label": SP.LABEL_CHART,
                   "statement": "one FIXED policy chart per coherent entity (the accepted NS1b construction at its NS1a "
                                "initialization gaze); never recentered; NOT physical head motion",
                   "construction": "x_C = normalize(b - (b.g0) g0), z_C = -g0, y_C = normalize(z_C x x_C); b = +X",
                   "charts": out_rows, "c172_equals_ns1b_chart": same172, "problems": problems}
            write_json(run / "charts/policy-charts.json", out)
    finally:
        write_json(run / "charts/charts-opened-files.json", guard_record(g))
    if problems:
        raise SystemExit(f"{PREFIX} STOP chart problems (before any execution): {problems}")
    return {"charts": len(out_rows), "c172_equals_ns1b": same172}


# ------------------------------------------------------------------ the initial contexts (unchanged NS1c construction)
def state_file(path: Path, st: dict, valid: np.ndarray) -> None:
    np.savez_compressed(path, ids_left=st["ids_left"], ids_right=st["ids_right"], raw_support_L=st["raw_support_L"],
                        raw_support_R=st["raw_support_R"], matcher_valid=np.asarray(valid, bool))


def contexts(ctx: Ctx) -> dict:
    run = ctx.run
    need(run / "charts/policy-charts.json", "charts")
    once(run / "contexts/contexts.json", "the initial controller contexts")
    cs = require_committed(ctx, "contexts")
    import ns1b_chart as CH
    import ns1b_core as B
    import ns1c2_core as CORE
    CH.ensure_policy_modules()
    el = read_json(run / "eligibility/coherent-seed-set.json")
    rows = {int(r["temporary_entity_id"]): r for r in scene_rows(el)}
    ranks = sorted({int(r["initialized_at_rank"]) for r in rows.values()})
    reads = [run / "eligibility/coherent-seed-set.json", run / "charts/policy-charts.json",
             ns1a("freeze/observation-freeze.json"), ns1a("freeze/seed-set-freeze.json"), ns1a(SP.NS1A_MAPS)]
    for r in ranks:
        reads += [ns1a(SP.ns1a_obs(r, d, n)) for d, n in (("acquisition", "calibration.json"),
                                                          ("acquisition", "rgb-observation.npz"),
                                                          ("oracle_aid", "reference-observation.npz"))]
    imp = ("context/controller-state.npz", "post/controller-state.npz", "post/evidence.npz",
           "fusion/fused-target-map.npz", "observation/acquisition/calibration.json", "freeze/observation-freeze.json",
           "post/post-action-probe.json", "fusion/fusion.json")
    reads += [ns1b(f) for f in imp]
    for sub in ("looks", "entities"):
        (run / "contexts" / sub).mkdir(parents=True, exist_ok=True)
    g = OpenGuard("ns1c2-contexts", reads, [run / "contexts"])
    try:
        with g:
            ofz, sfz = read_json(ns1a("freeze/observation-freeze.json")), read_json(ns1a("freeze/seed-set-freeze.json"))
            if sha256(ns1a(SP.NS1A_MAPS)) != sfz["files"][SP.NS1A_MAPS]:
                raise SystemExit(f"{PREFIX} STOP the NS1a seed maps changed after the seed freeze")
            chs = read_json(run / "charts/policy-charts.json")["charts"]
            looks, inputs = {}, {}
            for r in ranks:
                for d, n in (("acquisition", "calibration.json"), ("acquisition", "rgb-observation.npz"),
                             ("oracle_aid", "reference-observation.npz")):
                    rel = SP.ns1a_obs(r, d, n)
                    h = sha256(ns1a(rel))
                    if h != ofz["files"][rel]:
                        raise SystemExit(f"{PREFIX} STOP the NS1a look {rel} changed after its freeze (no rerender)")
                    inputs[rel] = h
                cal = read_json(ns1a(SP.ns1a_obs(r, "acquisition", "calibration.json")))
                rec_m, meta, st = B.matcher_state(cal, load_npz(ns1a(SP.ns1a_obs(r, "acquisition", "rgb-observation.npz"))),
                                                  load_npz(ns1a(SP.ns1a_obs(r, "oracle_aid", "reference-observation.npz"))))
                hr, ho = head_pose(cal)
                fixed = B.fixed_head(cal, hr, ho)
                if not fixed["ok"]:
                    raise SystemExit(f"{PREFIX} STOP the rank-{r} look is not the fixed head")
                p = run / f"contexts/looks/{SP.ns1a_rank_dir(r)}/controller-state.npz"
                p.parent.mkdir(parents=True, exist_ok=True)
                state_file(p, st, rec_m["valid"])
                looks[r] = {"calibration": cal, "state": st, "valid": np.asarray(rec_m["valid"], bool),
                            "instance": np.asarray(rec_m["instance_id"]), "meta": meta, "state_path": p,
                            "fixed_head": fixed}
            maps = load_npz(ns1a(SP.NS1A_MAPS))
            ents, diag = {}, {}
            for k, row in sorted(rows.items()):
                r = int(row["initialized_at_rank"])
                ch = chs[str(k)]
                rr = np.asarray(ch["R_HC"], np.float64)
                edir = run / f"contexts/entities/e{k:05d}"
                edir.mkdir(parents=True, exist_ok=True)
                lk = looks[r]
                pm0 = np.asarray(maps[SP.map_key(k, "provenance_mask")]).astype(np.uint64)
                support = {"controller_state_target_support": int((lk["valid"] & (lk["instance"] == k)).sum()),
                           "controller_state_target_pixels_L": int((lk["state"]["ids_left"] == k).sum()),
                           "ns1a_initialization_look_target_points": int(((pm0 & np.uint64(1)) != 0).sum())}
                if k == SP.CONTINUING:
                    rec, info = import_172(run, edir, lk, ch)
                    support["ns1b_action_look"] = info["ns1b_action_support"]
                else:
                    c_ctx, ad = B.build_context(k, lk["calibration"], lk["state"], lk["valid"], rr, (0.0, 0.0))
                    ev = B.evidence_arrays(c_ctx)
                    np.savez_compressed(edir / "evidence.npz", **ev)
                    m = B.map_arrays(B.load_surface_map(maps, k))
                    pids = [str(x) for x in m["patch_ids"]]
                    if not np.all(m["instance_id"] == k) or len(m["xyz_h"]) != int(row["final_surfels"]) or \
                            len(pids) != int(row["contributing_patches"]) or pids[0] != f"nb1c_gaze_{r:02d}":
                        raise SystemExit(f"{PREFIX} STOP entity {k}: the map is not its frozen NS1a map")
                    np.savez_compressed(edir / "map-H0.npz", **m)
                    rec = {"looks": [{"source": f"NS1a rank-{r:02d} initialization look",
                                      "calibration": f"ns1a:{SP.ns1a_obs(r, 'acquisition', 'calibration.json')}",
                                      "calibration_sha256": inputs[SP.ns1a_obs(r, "acquisition", "calibration.json")],
                                      "state": f"run:contexts/looks/{SP.ns1a_rank_dir(r)}/controller-state.npz",
                                      "state_sha256": sha256(lk["state_path"]), "local_gaze": [0.0, 0.0]}],
                           "visited": [[0.0, 0.0]], "current_local_gaze": [0.0, 0.0], "own_looks": 1}
                    info = {"adapter": ad, "evidence_cells": {n: int(v.sum()) for n, v in ev.items()}}
                rec.update({"temporary_entity_id": k, "initialization_rank": r, "chart_id": ch["chart_id"],
                            "chart_sha256": ch["R_HC_sha256"],
                            "evidence": {"path": f"run:contexts/entities/e{k:05d}/evidence.npz",
                                         "sha256": sha256(edir / "evidence.npz")}})
                mm = load_npz(edir / "map-H0.npz")
                rec["map"] = {"path": f"run:contexts/entities/e{k:05d}/map-H0.npz", "sha256": sha256(edir / "map-H0.npz"),
                              "surfels": int(len(mm["xyz_h"])), "patch_ids": [str(x) for x in mm["patch_ids"]]}
                rec["revision"] = CORE.revision(rec)
                c2_ = CORE.context_from_record(rec, run)
                if not arrays_equal(CORE.evidence_arrays(c2_), load_npz(edir / "evidence.npz")):
                    raise SystemExit(f"{PREFIX} STOP entity {k}: the context does not reload from its record")
                ents[str(k)] = rec
                diag[str(k)] = {**support, "north_star_map_surfels": rec["map"]["surfels"],
                                "map_local_forward_fraction": float((CH.to_chart(mm["xyz_h"], rr)[:, 2] < -1e-6).mean()),
                                **info}
            out = {"schema": "NS1c2-contexts-v1", "truth": SP.TRUTH_DERIVED, "code": cs,
                   "statement": "one accepted LocalPolicyContext per coherent entity, exactly as NS1c: 172 continues from "
                                "the accepted NS1b post-action context and map; every other entity from its frozen NS1a "
                                "map and saved initialization look (CONTROLLER OBSERVATION STATE only); no rerender",
                   "inputs_ns1a": inputs, "ranks": ranks,
                   "looks": {SP.ns1a_rank_dir(r): {"matcher": CORE.jsonable(v["meta"]), "fixed_head": v["fixed_head"],
                                                  "matcher_valid": int(v["valid"].sum()),
                                                  "state_sha256": sha256(v["state_path"])} for r, v in looks.items()},
                   "entities": ents, "diagnostics": diag}
            write_json(run / "contexts/contexts.json", out)
    finally:
        write_json(run / "contexts/contexts-opened-files.json", guard_record(g))
    return {"entities": len(ents), "own_looks": {k: v["own_looks"] for k, v in ents.items()}}


def import_172(run: Path, edir: Path, lk: dict, ch: dict) -> tuple[dict, dict]:
    """The accepted NS1b post-action context and map of entity 172, imported exactly (NS1c's construction)."""
    import ns1c2_core as CORE
    for rel in ("context/controller-state.npz", "post/controller-state.npz", "post/evidence.npz",
                "fusion/fused-target-map.npz", "observation/acquisition/calibration.json",
                "freeze/observation-freeze.json", "post/post-action-probe.json"):
        if sha256(ns1b(rel)) != SP.NS1B_PINS[rel]:
            raise SystemExit(f"{PREFIX} STOP the accepted NS1b file {rel} changed")
    if not arrays_equal(load_npz(lk["state_path"]), load_npz(ns1b("context/controller-state.npz"))):
        raise SystemExit(f"{PREFIX} STOP the NS1c2 rank-6 controller state differs from NS1b's (one look, one state)")
    post = load_npz(ns1b("post/controller-state.npz"))
    p = run / "contexts/looks/ns1b-action/controller-state.npz"
    p.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(p, **post)
    ev = load_npz(ns1b("post/evidence.npz"))
    np.savez_compressed(edir / "evidence.npz", **ev)
    fm = load_npz(ns1b("fusion/fused-target-map.npz"))
    np.savez_compressed(edir / "map-H0.npz", **fm)
    copies = {"ns1b-action state": arrays_equal(load_npz(p), post),
              "evidence": arrays_equal(load_npz(edir / "evidence.npz"), ev),
              "map": arrays_equal(load_npz(edir / "map-H0.npz"), fm)}
    if not all(copies.values()):
        raise SystemExit(f"{PREFIX} STOP the 172 import is not exact: {copies}")
    if (len(fm["xyz_h"]) != SP.NS1B_172["map_surfels"] or not np.all(fm["instance_id"] == SP.CONTINUING)
            or [str(x) for x in fm["patch_ids"]] != SP.NS1B_172["patch_ids"]):
        raise SystemExit(f"{PREFIX} STOP the NS1b post-action map of 172 is not 21,243 surfels of 172")
    pp = read_json(ns1b("post/post-action-probe.json"))
    if pp["own_looks"] != SP.NS1B_172["own_looks"] or pp["visited"] != SP.NS1B_172["visited"]:
        raise SystemExit(f"{PREFIX} STOP the NS1b post-action context is not 2 own looks at (0, 0), (0, -5)")
    rank = SP.NS1B_172["rank"]
    rec = {"looks": [{"source": f"NS1a rank-{rank:02d} initialization look",
                      "calibration": f"ns1a:{SP.ns1a_obs(rank, 'acquisition', 'calibration.json')}",
                      "calibration_sha256": sha256(ns1a(SP.ns1a_obs(rank, "acquisition", "calibration.json"))),
                      "state": f"run:contexts/looks/{SP.ns1a_rank_dir(rank)}/controller-state.npz",
                      "state_sha256": sha256(lk["state_path"]), "local_gaze": [0.0, 0.0]},
                     {"source": "NS1b action 1 (ns1b_action_01, accepted)",
                      "calibration": "ns1b:observation/acquisition/calibration.json",
                      "calibration_sha256": SP.NS1B_PINS["observation/acquisition/calibration.json"],
                      "state": "run:contexts/looks/ns1b-action/controller-state.npz", "state_sha256": sha256(p),
                      "local_gaze": list(SP.NS1B_172["gaze"])}],
           "visited": [list(v) for v in SP.NS1B_172["visited"]], "current_local_gaze": list(SP.NS1B_172["gaze"]),
           "own_looks": SP.NS1B_172["own_looks"],
           "imported_from_ns1b": {"evidence": "post/evidence.npz", "map": "fusion/fused-target-map.npz",
                                  "rank6_state": "context/controller-state.npz",
                                  "action_state": "post/controller-state.npz", "arrays_equal": copies}}
    r = np.asarray(ch["R_HC"], np.float64)
    rebuilt = CORE.evidence_arrays(CORE.rebuild_context({**rec, "temporary_entity_id": SP.CONTINUING}, run, r))
    if not arrays_equal(rebuilt, ev):
        raise SystemExit(f"{PREFIX} STOP the NS1b evidence of 172 is not reproduced from its two looks")
    info = {"ns1b_action_support": {"controller_state_target_support": int(pp["matcher_target_valid_points"]),
                                    "controller_state_target_pixels_L": int((post["ids_left"] == SP.CONTINUING).sum()),
                                    "north_star_target_points": int(read_json(ns1b("fusion/fusion.json"))[
                                        "measured_points"])},
            "evidence_cells": {n: int(v.sum()) for n, v in ev.items()}, "evidence_rebuilt_equal": True}
    return rec, info


# ------------------------------------------------------------------ probes, entity records, scene states
def probe_reads(run: Path, recs: dict) -> list[Path]:
    out = []
    for rec in recs.values():
        for look in rec["looks"]:
            out += [res(look["calibration"], run), res(look["state"], run)]
        out += [res(rec["evidence"]["path"], run), res(rec["map"]["path"], run)]
        if rec.get("probe"):
            out.append(res(rec["probe"]["path"], run))
    return sorted(set(out))


def probe_file_record(entity: int, computed_at: str, revision, out: dict, extra: dict | None = None) -> dict:
    import ns1c2_core as CORE
    return {"schema": "NS1c2-probe-v1", "truth": SP.TRUTH_DERIVED, "entity": int(entity), "computed_at": computed_at,
            "revision": list(revision), "phase_at_probe": "NORMAL", "gate_called": False,
            "probe": CORE.jsonable(out), **(extra or {})}


def with_status(rec: dict, st, probe_out: dict | None = None) -> dict:
    import ns1c2_core as CORE
    rec = dict(rec)
    rec["status"] = CORE.status_record(st)
    if probe_out is not None:
        rec["proposal"] = CORE.proposal_summary(probe_out)
        rec["policy"] = CORE.policy_summary(probe_out)
    return rec


def scene_table(ents: dict) -> list[dict]:
    import ns1c2_core as CORE
    return [CORE.entity_row(ents[k]) for k in sorted(ents, key=int)]


def policy_configuration() -> dict:
    import fsg6f_public as PUB
    from fov3d.control import frontier_config
    from fov3d.experiments.classroom_oracle import config as public
    import tools.classroom_oracle1_epistemic as EPL
    ev = EPL.make_evidence()
    return {"SURFACE_FRONTIER": dict(PUB.SURFACE_FRONTIER), "SURFACE_FRONTIER_facade": dict(
        frontier_config.SURFACE_FRONTIER), "FSG6F_FUSION": dict(PUB.FUSION), "OBJECT_ID": int(PUB.OBJECT_ID),
            "CYCLOPEAN_GRID_DEG": float(public.CYCLOPEAN_GRID_DEG), "cyclopean_chart_shape": list(ev.shape),
            "cyclopean_domain_deg": [ev.yaw_min_deg, ev.yaw_max_deg, ev.pitch_min_deg, ev.pitch_max_deg],
            "FUSION": dict(public.FUSION), "gate": "controller02.final_look_gate_v1 (accepted; RESIDUE only)"}


# ------------------------------------------------------------------ the initial NORMAL probe (no gate)
def initial_probe(ctx: Ctx) -> dict:
    run = ctx.run
    need(run / "contexts/contexts.json", "contexts")
    once(run / "initial-probe/initial-service-table.json", "the initial probe of every coherent entity")
    cs = require_committed(ctx, "initial-probe")
    import ns1b_chart as CH
    import ns1c2_core as CORE
    import ns1c2_phase as PH
    from fov3d.control import controller02 as c2
    import ns1a_core  # noqa: F401
    CH.ensure_policy_modules()
    import fsg6f_frontier  # noqa: F401
    recs = read_json(run / "contexts/contexts.json")["entities"]
    budget = CORE.budget_live()
    ns1c_probes = {k: f"initial-probe/probes/e{int(k):05d}.json" for k in recs
                   if (ns1c(f"initial-probe/probes/e{int(k):05d}.json")).exists()}
    man = ns1c_manifest()
    reads = probe_reads(run, recs) + [run / "contexts/contexts.json", run / "charts/policy-charts.json",
                                      run / "eligibility/coherent-seed-set.json", ns1b("post/post-action-probe.json"),
                                      ns1c("manifest.json")] + [ns1c(r) for r in ns1c_probes.values()]
    (run / "initial-probe/probes").mkdir(parents=True, exist_ok=True)
    (run / "scene").mkdir(parents=True, exist_ok=True)
    g = OpenGuard("ns1c2-initial-probe", reads, [run / "initial-probe", run / "scene"])
    problems, table, outs = [], [], {}
    try:
        with g, PH.GateGuard(c2.ScenePhase.NORMAL.value, "initial-probe") as gg:
            el = read_json(run / "eligibility/coherent-seed-set.json")
            chs = read_json(run / "charts/policy-charts.json")["charts"]
            nbp = read_json(ns1b("post/post-action-probe.json"))["probe"]
            ns1c_verify(list(ns1c_probes.values()), man)
            repro, ns1c_eq = None, {}
            for k in sorted(recs, key=int):
                rec = recs[k]
                try:
                    out = CORE.probe_entity(rec, run, chs[k], f"initial NORMAL probe entity {k}")
                except PH.GateOutsideResidue:
                    raise
                except Exception as exc:  # noqa: BLE001  (a refusal of the accepted code is Outcome 4, recorded)
                    problems.append(f"entity {k}: the accepted probe raised {type(exc).__name__}: {exc}")
                    continue
                rot = CORE.rotation_invariance(rec, run, chs[k], out)
                if not all(r_["pass"] for r_ in rot):
                    problems.append(f"entity {k}: baseline-rotation invariance failed")
                if out["adapter"]["calls"]["P3"] != 0:
                    problems.append(f"entity {k}: P3 (the gate's predicted calibration) was called in NORMAL")
                if out["proposal"] is not None and out["proposal"]["roundtrip_error_deg"] > SP.GAZE_ROUNDTRIP_TOL_DEG:
                    problems.append(f"entity {k}: the chart / world gaze round trip fails")
                if int(k) == SP.CONTINUING:
                    diffs = CORE.policy_comparison(nbp, out)
                    p = out["proposal"] or {}
                    exp = {"state": out["state"], "source": p.get("source"), "local_gaze_deg": p.get("local_gaze_deg")}
                    repro = {"differences": diffs[:20], "difference_count": len(diffs), "got": exp,
                             "expected": SP.NS1B_POST_EXPECTED, "accepted_record": "ns1b:post/post-action-probe.json",
                             "reproduced": not diffs and exp == SP.NS1B_POST_EXPECTED}
                    if not repro["reproduced"]:
                        problems.append(f"HARD STOP: the NS1b post-action probe of 172 is not reproduced: {diffs[:5]}")
                if k in ns1c_probes:
                    d = CORE.policy_comparison(read_json(ns1c(ns1c_probes[k]))["probe"], out)
                    ns1c_eq[k] = {"differences": d[:5], "equal": not d}
                    if d:
                        problems.append(f"entity {k}: the NORMAL probe's policy part differs from NS1c's {d[:3]}")
                elif not ctx.dev:
                    problems.append(f"entity {k}: no NS1c initial probe to compare")
                outs[k] = out
                pth = run / f"initial-probe/probes/e{int(k):05d}.json"
                write_json(pth, probe_file_record(int(k), "initial-probe", rec["revision"], out,
                                                  {"baseline_rotation_invariance": rot}))
                recs[k] = {**rec, "probe": {"path": f"run:initial-probe/probes/e{int(k):05d}.json",
                                            "sha256": sha256(pth), "revision": rec["revision"], "provenance": "fresh",
                                            "computed_at": "initial-probe"}}
            if not problems:
                v, f = CORE.vergence_focus()
                ids = sorted(int(k) for k in recs)
                m = PH.SceneMachine(ids, budget=budget, vergence=v, focus=f)
                m.resume_initialized({i: int(recs[str(i)]["own_looks"]) for i in ids}, current=SP.CONTINUING, bout=1,
                                     step=0, probe=lambda i: CORE.probe_result(
                                         outs[str(i)], i, {"probe_path": recs[str(i)]["probe"]["path"],
                                                           "revision": recs[str(i)]["revision"]}),
                                     revision=lambda i: CORE.revision(recs[str(i)]))
                ents = {k: with_status(recs[k], m.statuses[int(k)], outs[k]) for k in recs}
                for k in sorted(ents, key=int):
                    o, e = outs[k], ents[k]
                    p = o["proposal"]
                    table.append({"temporary_entity_id": int(k), "initialization_rank": e["initialization_rank"],
                                  "map_surfels": e["map"]["surfels"], "own_looks": e["own_looks"],
                                  "current_local_gaze": e["current_local_gaze"],
                                  "fsg6f": o["summary"]["fsg6f"]["reason"],
                                  "cyclopean": (o["summary"].get("cyclopean") or {}).get("reason"),
                                  "proposal_source": None if p is None else p["source"],
                                  "proposed_local_gaze": None if p is None else p["local_gaze_deg"],
                                  "proposed_H0_gaze": None if p is None else p["world_gaze_deg"],
                                  "local_state": e["status"]["local"], "disposition": e["status"]["disposition"],
                                  "label": e["status"]["label"], "gate_called": False,
                                  "ns1c_policy_equal": (ns1c_eq.get(k) or {}).get("equal")})
                scene = {"schema": "NS1c2-scene-state-v1", "truth": SP.TRUTH_DERIVED, "label": "initial",
                         "global_step": -1, "code": cs, "phase": m.phase.value, "current": SP.CONTINUING,
                         "previous": None, "attention_bout": 1, "executed_actions": 0, "new_actions": 0,
                         "budget": budget, "cap": None, "scene_ids": ids, "coherent_ids": el["coherent_ids"],
                         "deferred": [{"temporary_entity_id": r_["temporary_entity_id"], "state": SP.DEFERRED_STATE,
                                       "contributing_patches": r_["contributing_patches"], "in_scheduler": False}
                                      for r_ in el["deferred"]],
                         "entities": ents, "events": [], "machine": m.to_json(), "stopped": False, "stop": None,
                         "last_decision": None, "last_action": None, "gate_guard": gg.record(),
                         "table": scene_table(ents)}
                write_json(run / SP.scene_state_rel("initial"), scene)
            tab = {"schema": "NS1c2-initial-service-table-v1", "truth": SP.TRUTH_DERIVED, "code": cs,
                   "statement": "every coherent entity probed exactly once before any replay or render under NORMAL "
                                "semantics: the accepted FSG6f -> Cyclopean probe under its fixed chart, NO final-look "
                                "gate; ACTIONABLE iff the ProbeResult carries an action (any source)",
                   "budget": budget, "rows": table, "ns1b_reproduction": repro, "ns1c_policy_equality": ns1c_eq,
                   "expected_from_ns1c_diagnostic": {"all_actionable": True, "fsg6f": [123, 172],
                                                     "cyclopean": [9, 12, 129, 202, 204, 212, 230, 231]},
                   "problems": problems, "gate_guard": gg.record(),
                   "deferred": [{"temporary_entity_id": r_["temporary_entity_id"], "state": SP.DEFERRED_STATE,
                                 "contributing_patches": r_["contributing_patches"]} for r_ in el["deferred"]],
                   "policy_configuration_used": CORE.jsonable(policy_configuration())}
            write_json(run / "initial-probe/initial-service-table.json", tab)
    finally:
        write_json(run / "initial-probe/initial-probe-opened-files.json", guard_record(g))
    if problems:
        raise SystemExit(f"{PREFIX} STOP initial probe (no replay, no render): {problems}")
    return {"rows": [[r_["temporary_entity_id"], r_["label"], r_["proposal_source"]] for r_ in table],
            "ns1b_reproduced": repro["reproduced"] if repro else None, "gate_calls": gg.record()["calls"]}


# ------------------------------------------------------------------ the scene state of a step
def prev_scene_rel(step: int) -> str:
    return SP.scene_state_rel("initial" if step == 0 else f"after-step-{step - 1:02d}")


def latest_scene(run: Path) -> tuple[str, dict]:
    sts = sorted((run / "scene").glob("state-after-step-*.json"))
    rel = str(sts[-1].relative_to(run)) if sts else SP.scene_state_rel("initial")
    return rel, read_json(run / rel)


def obs_root(ctx: Ctx) -> tuple[Path, str]:
    """Where a step's observation products live: NS1c's step directory (read-only) for the prefix, its own otherwise."""
    if SP.is_prefix(ctx.step):
        return ns1c(SP.step_dir(ctx.step)), f"ns1c:{SP.step_dir(ctx.step)}"
    return ctx.sd(), f"run:{SP.step_dir(ctx.step)}"


def process_guard(ctx: Ctx):
    """The accepted NoProcessGuard for the prefix stages (no process, hence no Blender); a null context otherwise."""
    import contextlib
    if SP.is_prefix(ctx.step):
        from fov3d.experiments.classroom_oracle.controller02 import NoProcessGuard
        return NoProcessGuard()
    return contextlib.nullcontext()


def process_record(pg) -> dict:
    return {"guard": "fov3d.experiments.classroom_oracle.controller02.NoProcessGuard",
            "events": list(pg.EVENTS), "attempts": list(pg.attempts)} if hasattr(pg, "attempts") else None


def plan_to_json(plan: dict) -> dict:
    import ns1c2_phase as PH
    a = plan.get("action")
    return {**{k: v for k, v in plan.items() if k not in ("action", "before")},
            "action": None if a is None else {"target_id": int(a.target_id), "gaze_deg": list(a.gaze_yaw_pitch_deg),
                                              "source": a.source},
            "before": None if plan.get("before") is None else PH.status_to_json(plan["before"])}


def plan_from_json(p: dict):
    import ns1c2_core as CORE
    import ns1c2_phase as PH
    from fov3d.control import integrated as ic
    v, f = CORE.vergence_focus()
    a = p["action"]
    return {**p, "action": ic.Observe(int(a["target_id"]), tuple(a["gaze_deg"]), v, f, a["source"]),
            "before": PH.status_from_json(p["before"])}


# ------------------------------------------------------------------ schedule (the accepted Controller-02 decision)
def schedule(ctx: Ctx) -> dict:
    run, k = ctx.run, int(ctx.step)
    sd = ctx.sd()
    need(run / prev_scene_rel(k), f"the scene state before step {k}")
    if (run / SP.scene_state_rel(f"after-step-{k:02d}")).exists() or (run / SP.step_dir(k + 1)).exists():
        raise Refused(f"{PREFIX} REFUSED step {k} is not the next step")
    once(sd / "plan/decision.json", f"the decision of step {k}")
    if (run / "scene/terminal.json").exists():
        raise Refused(f"{PREFIX} REFUSED the scene already reached a terminal record")
    prefix = SP.is_prefix(k)
    if not prefix:
        need(run / "freeze/divergence-freeze.json", "the frozen divergence record")
    cs = require_committed(ctx, "schedule")
    import ns1b_chart as CH
    import ns1c2_core as CORE
    import ns1c2_phase as PH
    from fov3d.control import controller02 as c2
    CH.ensure_policy_modules()
    import ns1a_core  # noqa: F401
    import fsg6f_frontier  # noqa: F401
    prev = read_json(run / prev_scene_rel(k))
    try:
        CORE.require_not_stopped(prev)
    except CORE.ProcessRefused as exc:
        raise Refused(f"{PREFIX} REFUSED {exc}")
    div = read_json(run / "divergence/divergence.json") if not prefix else None
    cap = None if prefix else int(div["cap"])
    reads = [run / prev_scene_rel(k), run / "charts/policy-charts.json"] + probe_reads(run, prev["entities"])
    if not prefix:
        reads += [run / "divergence/divergence.json", run / "freeze/divergence-freeze.json"]
    ns1c_rels = [f"{SP.step_dir(k)}/plan/decision.json", f"{SP.step_dir(k)}/plan/planned-calibration.json"]
    if prefix:
        reads += [ns1c("manifest.json")] + [ns1c(r) for r in ns1c_rels]
    (sd / "plan").mkdir(parents=True, exist_ok=True)
    g = OpenGuard(f"ns1c2-schedule-{k:02d}", reads, [sd / "plan", run / "scene"])
    pg = process_guard(ctx)
    terminal, failure = None, None
    try:
        with g, pg, PH.GateGuard(prev["phase"], f"schedule step {k}") as gg:
            if not prefix and sha256(run / "divergence/divergence.json") != \
                    read_json(run / "freeze/divergence-freeze.json")["files"]["divergence/divergence.json"]:
                raise SystemExit(f"{PREFIX} STOP the divergence record changed after its freeze")
            m = PH.SceneMachine.from_json(prev["machine"])
            chs = read_json(run / "charts/policy-charts.json")["charts"]
            statuses = [[int(s.instance_id), s.label] for s in sorted(m.statuses.values(), key=lambda s: s.instance_id)]
            sched = c2.schedule_normal(m.current, m.statuses.values())
            cal0 = json.loads(res(prev["entities"][str(SP.CONTINUING)]["looks"][0]["calibration"], run).read_text())
            hr, ho = head_pose(cal0)
            gate_records = []

            def final_gate(i, proposal):
                gg.phase = m.phase.value
                rec = prev["entities"][str(i)]
                cached = read_json(res(rec["probe"]["path"], run))["probe"]
                verdict, detail = CORE.residue_gate(rec, run, chs[str(i)], cached, proposal, hr, ho,
                                                    f"residue gate entity {i} (step {k})")
                gate_records.append({"object": i, "phase": m.phase.value, **detail})
                gg.phase = m.phase.value
                return verdict
            n_ev = len(m.events)
            plan = m.decide(final_gate, None if prefix else SP.PREFIX_STEPS + cap)
            out = {"schema": "NS1c2-decision-v1", "truth": SP.TRUTH_DERIVED, "code": cs, "global_step": k,
                   "prefix": prefix, "kind": plan["kind"],
                   "statement": "the accepted Controller-02 scene loop (controller02.schedule_normal over NORMAL-serviceable "
                                "objects; RESIDUE only when it returns None) through the resumable adapter",
                   "scheduler_decision": {"function": "fov3d.control.controller02.schedule_normal",
                                          "current_before": prev["current"], "statuses": statuses,
                                          "result": None if sched is None else {"kind": sched.kind,
                                                                                "target_id": sched.target_id,
                                                                                "reason": sched.reason}},
                   "phase_before": prev["phase"], "phase_after_decide": m.phase.value,
                   "events_in_decide": m.events[n_ev:], "residue_gate_records": gate_records,
                   "gate_guard": gg.record(), "new_actions_before": prev["new_actions"], "cap": cap,
                   "scene_state_before": {"path": prev_scene_rel(k), "sha256": sha256(run / prev_scene_rel(k))}}
            if plan["kind"] in ("closed", "cap"):
                terminal = plan
                out["terminal"] = CORE.jsonable({k_: v for k_, v in plan.items()})
                out["machine_after_decide"] = m.to_json()
                write_json(sd / "plan/decision.json", out)
                reading = ("Outcome 3 - ordinary and residue work exhausted before a second-entity action (not a "
                           "Classroom scene closure)" if plan["kind"] == "closed"
                           else "Outcome 4 - the post-divergence safety cap was reached")
                write_json(run / "scene/terminal.json", {**out, "outcome_reading": reading})
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
                plan_g = CORE.plan_action(prop, chs[str(t)], hr, ho)
                if (plan_g["roundtrip_error_deg"] > SP.GAZE_ROUNDTRIP_TOL_DEG
                        or plan_g["world_gaze_deg"] != prop["world_gaze_deg"]
                        or not plan_g["physical_calibration_test"]["ok"]):
                    raise SystemExit(f"{PREFIX} STOP the world gaze / planned calibration of step {k} fails (Outcome 4)")
                b = plan_g.pop("planned_calibration_bytes")
                planned = plan_g.pop("planned_calibration")
                (sd / "plan/planned-calibration.json").write_bytes(b)
                out["plan"] = plan_to_json(plan)
                out["machine_after_decide"] = m.to_json()
                out["scheduler_reason"] = plan["reason"]
                out["attention_bout"] = plan["attention_bout"]
                out["action"] = {"global_step": k, "target": t, "source": prop["source"], "phase": plan["phase"],
                                 "local_gaze_deg": plan_g["local_gaze_deg"], "world_gaze_deg": plan_g["world_gaze_deg"],
                                 "planned_calibration_sha256": hashlib.sha256(b).hexdigest(),
                                 "patch_id": SP.patch_id(k), "own_looks_before": rec_t["own_looks"],
                                 "chart_id": rec_t["chart_id"], "chart_sha256": rec_t["chart_sha256"],
                                 "proposal_probe": rec_t["probe"], "status_before": rec_t["status"]}
                out["plan_geometry"] = {**plan_g, "planned_gaze_H0_deg": list(planned["gaze_yaw_pitch_deg"])}
                out["previous_target"] = prev["current"]
                out["target_transition"] = "retain" if prev["current"] == t else f"{prev['current']}->{t}"
                if prefix:
                    ns1c_verify(ns1c_rels)
                    nd = read_json(ns1c(f"{SP.step_dir(k)}/plan/decision.json"))
                    na = nd["action"]
                    cmp_ = {"target": (t, int(na["target"])), "scheduler": (plan["decision"], nd["scheduler_decision"]["reason"]),
                            "source": (prop["source"], na["source"]),
                            "local_gaze_deg": (plan_g["local_gaze_deg"], na["local_gaze_deg"]),
                            "world_gaze_deg": (plan_g["world_gaze_deg"], na["world_gaze_deg"]),
                            "planned_calibration_sha256": (out["action"]["planned_calibration_sha256"],
                                                           na["planned_calibration_sha256"]),
                            "attention_bout": (plan["attention_bout"], nd["attention_bout"])}
                    diffs = {kk: vv for kk, vv in cmp_.items() if vv[0] != vv[1]}
                    out["ns1c_prefix_comparison"] = {"ns1c_decision": f"ns1c:{SP.step_dir(k)}/plan/decision.json",
                                                     "fields": {kk: list(vv) for kk, vv in cmp_.items()},
                                                     "differences": {kk: list(vv) for kk, vv in diffs.items()},
                                                     "equal": not diffs and t == SP.CONTINUING
                                                     and plan["decision"] == "retain" and prop["source"] == "fsg6f"}
                    if not out["ns1c_prefix_comparison"]["equal"]:
                        failure = f"prefix step {k} differs from NS1c: {diffs}"
                write_json(sd / "plan/decision.json", out)
    finally:
        write_json(sd / "plan/plan-opened-files.json", guard_record(g, {"process_guard": process_record(pg)}))
    if failure:
        raise SystemExit(f"{PREFIX} STOP {failure} (Outcome 4: the saved prefix is not used further)")
    if terminal is not None:
        if terminal["kind"] == "cap":
            raise SystemExit(f"{PREFIX} STOP the post-divergence cap is reached (Outcome 4)")
        return {"kind": terminal["kind"]}
    return {"kind": out["kind"], "target": out["action"]["target"], "reason": out["scheduler_reason"],
            "phase": out["action"]["phase"], "source": out["action"]["source"],
            "local": out["action"]["local_gaze_deg"], "world": out["action"]["world_gaze_deg"]}


def require_action(ctx: Ctx, what: str) -> dict:
    sd = ctx.sd()
    need(sd / "plan/decision.json", f"schedule (step {ctx.step})")
    d = read_json(sd / "plan/decision.json")
    if d.get("kind") not in ("attend", "final_residue") or not d.get("action"):
        raise Refused(f"{PREFIX} REFUSED {what} is not applicable: step {ctx.step} has no scheduled action "
                      f"({d.get('kind')})")
    return d


def require_new_step(ctx: Ctx, what: str) -> None:
    if SP.is_prefix(ctx.step):
        raise Refused(f"{PREFIX} REFUSED {what} never runs for a prefix step ({ctx.step}): NS1c's measured observation "
                      "is replayed read-only, never re-rendered")


def require_prefix_step(ctx: Ctx, what: str) -> None:
    if not SP.is_prefix(ctx.step):
        raise Refused(f"{PREFIX} REFUSED {what} is a prefix-only stage")


# ------------------------------------------------------------------ replay (prefix steps only; no Blender)
def observation_files() -> list[str]:
    return [SP.ACQ_RUN_REL] + [f"{SP.OBS_ACQ}/{n}" for n in SP.OBS_ACQ_FILES] + [f"{SP.OBS_AID}/{n}"
                                                                                 for n in SP.OBS_AID_FILES]


CORR_FILES = ("correspondence/oracle-correspondences.npz", "correspondence/oracle-summary.json",
              "correspondence/core-class-map.npz", "correspondence/correspondence-opened-files.json")
GEOM_FILES = ("geometry/left-core-rays.npz", "geometry/epipolar-result.npz", "geometry/geometry-summary.json",
              "geometry/geometry-opened-files.json")
SEG_FILES = ("segmentation/local-identity.npz", "segmentation/identity-summary.json")


def replay(ctx: Ctx) -> dict:
    run, sd, k = ctx.run, ctx.sd(), int(ctx.step)
    require_prefix_step(ctx, "replay")
    d = require_action(ctx, "replay")
    once(sd / "replay/replay.json", f"the replay of prefix step {k}")
    cs = require_committed(ctx, "replay")
    base = SP.step_dir(k)
    rels = ([f"{base}/{f}" for f in observation_files()] + [f"{base}/{f}" for f in CORR_FILES + GEOM_FILES + SEG_FILES]
            + [f"{base}/freeze/{n}" for n in ("observation-freeze.json", "correspondence-freeze.json",
                                              "geometry-freeze.json")]
            + [f"{base}/segmentation/segmentation-opened-files.json"])
    reads = [ns1c("manifest.json")] + [ns1c(r) for r in rels] + [sd / "plan/decision.json",
                                                                 sd / "plan/planned-calibration.json"]
    (sd / "replay").mkdir(parents=True, exist_ok=True)
    g = OpenGuard(f"ns1c2-replay-{k:02d}", reads, [sd / "replay"])
    pg = process_guard(ctx)
    try:
        with g, pg:
            man = ns1c_manifest()
            hashes = ns1c_verify(rels, man)
            pins = {rel: hashes[f"{base}/{rel}"] for rel in SP.NS1C_PREFIX_PINS[k] if f"{base}/{rel}" in hashes}
            bad = {r: h for r, h in pins.items() if h != SP.NS1C_PREFIX_PINS[k][r]}
            nroot = ns1c(base)
            for fz in ("freeze/observation-freeze.json", "freeze/correspondence-freeze.json", "freeze/geometry-freeze.json"):
                verify_record_hashes(nroot, fz)
            ar = read_json(nroot / SP.ACQ_RUN_REL)
            acq = read_json(nroot / f"{SP.OBS_ACQ}/acquisition.json")
            plan_b = (sd / "plan/planned-calibration.json").read_bytes()
            physical = {
                "calibration_bytes_equal_ns1c2_plan": (nroot / f"{SP.OBS_ACQ}/calibration.json").read_bytes() == plan_b,
                "spp": ar["spp"] == acq["spp"] == acq["settings"]["samples"] == SP.SPP,
                "exr_samples": ar["exr_samples_lr"] == {"L": str(SP.SPP), "R": str(SP.SPP)},
                "seeds": acq["render_seeds_lr"] == SP.SEEDS, "device": acq["device"] == SP.DEVICE,
                "denoising_off": acq["settings"]["denoising"] is False,
                "adaptive_off": acq["settings"]["adaptive_sampling"] is False,
                "box_filter": acq["settings"]["pixel_filter"] == "BOX" and acq["settings"]["filter_width"] == 1.0,
                "catalog_seal": ar["catalog_seal"]["sha256"] == SP.NS1A_CATALOG_SEAL,
                "target": int(ar["target"]) == int(d["action"]["target"]) == SP.CONTINUING,
                "gaze_H0": list(ar["gaze_H0_deg"]) == list(d["action"]["world_gaze_deg"]),
                "not_rehearsal": not acq.get("rehearsal"),
            }
            out = {"schema": "NS1c2-replay-v1", "truth": SP.TRUTH_ORACLE, "code": cs, "global_step": k,
                   "label": SP.LABEL_NS1C_REPLAY,
                   "statement": "NS1c's measured observation, PERFECT correspondence, spherical geometry and local "
                                "identity of this step, verified in place against NS1c's own freezes, the pinned NS1c "
                                "manifest and NS1c2's literal pins; nothing copied, nothing rendered (no process may "
                                "start in this stage)",
                   "source": f"ns1c:{base}", "verified_files": hashes, "literal_pins": pins,
                   "literal_pin_mismatches": sorted(bad), "physical": physical,
                   "render_seconds_lr_of_ns1c": ar["render_seconds_lr"],
                   "ok": not bad and all(physical.values())}
            write_json(sd / "replay/replay.json", out)
    finally:
        write_json(sd / "replay/replay-opened-files.json", guard_record(g, {"process_guard": process_record(pg)}))
    if not out["ok"]:
        raise SystemExit(f"{PREFIX} STOP the NS1c prefix step {k} does not verify: {bad} {physical} (Outcome 4)")
    return {"files": len(hashes), "physical": all(physical.values())}


# ------------------------------------------------------------------ Blender (preflight / acquire of a new step)
def blender(ctx: Ctx, args: list[str], log: Path, factory: bool = False) -> None:
    log.parent.mkdir(parents=True, exist_ok=True)
    cmd = [SP.BLENDER, "-b"] + (["--factory-startup"] if factory else [str(REPO / SP.BLEND)])
    cmd += ["--python-exit-code", "1", "-P", str(HERE / "ns1c2_render.py"), "--"] + args
    with open(log, "w") as f:
        p = subprocess.run(cmd, cwd=REPO, stdout=f, stderr=subprocess.STDOUT)
    text = log.read_text(errors="replace")
    if p.returncode != 0 or "[ns1c2-render] COMPLETE" not in text or "[ns1c2-render] FAILED" in text:
        raise SystemExit(f"{PREFIX} STOP Blender failed (exit {p.returncode}); see {log}")


def preflight(ctx: Ctx) -> dict:
    sd = ctx.sd()
    require_new_step(ctx, "preflight")
    require_action(ctx, "preflight")
    once(sd / "preflight/preflight.json", f"the preflight of step {ctx.step}")
    require_committed(ctx, "preflight")
    if ctx.rehearsal_spp is None:
        if sha256(REPO / SP.BLEND) != SP.BLEND_SHA256:
            raise SystemExit(f"{PREFIX} STOP the Classroom blend changed")
        blender(ctx, ["--mode", "preflight", "--step-dir", str(sd)], sd / "preflight/blender.log")
    else:
        write_json(sd / "preflight/preflight.json", {"schema": "NS1c2-preflight-v1", "rendered": False,
                                                       "rehearsal": True, "statement": "rehearsal: no Classroom"})
    return {k: v for k, v in read_json(sd / "preflight/preflight.json").items() if k in ("rendered", "gaze_H0_deg")}


def acquire(ctx: Ctx) -> dict:
    sd = ctx.sd()
    require_new_step(ctx, "acquire")
    d = require_action(ctx, "acquire")
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
    return {"gaze_H0_deg": ar["gaze_H0_deg"], "budget": ar["budget"], "spp": ar["spp"], "target": ar["target"]}


# ------------------------------------------------------------------ freeze-observation / PERFECT correspondence / geometry / id
def freeze_observation(ctx: Ctx) -> dict:
    sd = ctx.sd()
    require_new_step(ctx, "freeze-observation")
    d = require_action(ctx, "freeze-observation")
    need(sd / SP.ACQ_RUN_REL, "acquire")
    once(sd / "freeze/observation-freeze.json", f"the observation freeze of step {ctx.step}")
    cs = require_committed(ctx, "freeze-observation")
    files = observation_files()
    g = OpenGuard(f"ns1c2-freeze-observation-{ctx.step:02d}", [sd / f for f in files] + [
        sd / "plan/planned-calibration.json", sd / "plan/decision.json"], [sd / "freeze"])
    try:
        with g:
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
            if not ctx.dev and (ar["spp"] != SP.SPP or ar["exr_samples_lr"] != {"L": str(SP.SPP), "R": str(SP.SPP)}
                                or ar["catalog_seal"]["sha256"] != SP.NS1A_CATALOG_SEAL):
                problems.append("spp / EXR samples / catalog seal")
            with np.load(sd / f"{SP.OBS_ACQ}/rgb-observation.npz") as z:
                if sorted(z.files) != ["rgb_L", "rgb_R"]:
                    problems.append(f"rgb keys {z.files}")
            with np.load(sd / f"{SP.OBS_AID}/reference-observation.npz") as z:
                if sorted(z.files) != sorted(("instance_L", "instance_R", "position_w_L", "position_w_R")):
                    problems.append(f"reference keys {z.files}")
            if problems:
                raise SystemExit(f"{PREFIX} STOP observation problems: {problems}")
            fz = {"schema": "NS1c2-observation-freeze-v1", "truth": SP.TRUTH_ORACLE, "frozen_utc": utc(), "code": cs,
                  "global_step": ctx.step, "target": d["action"]["target"],
                  "statement": "the step's one binocular observation at the mapped H0 gaze; never re-rendered. The "
                               "sealed catalog is NOT opened: its Blender-recorded seal is carried", "spp": ar["spp"],
                  "catalog_seal": ar["catalog_seal"], "files": hashes}
            write_json(sd / "freeze/observation-freeze.json", fz)
    finally:
        write_json(sd / "freeze/observation-freeze-opened-files.json", guard_record(g))
    return {"files": len(hashes), "spp": ar["spp"]}


def perfect_correspondence(ctx: Ctx) -> dict:
    sd = ctx.sd()
    require_new_step(ctx, "perfect-correspondence")
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
    g = OpenGuard(f"ns1c2-oracle-{ctx.step:02d}", [cal, ref, sd / "freeze/observation-freeze.json"], [odir])
    try:
        with g:
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
            summary = {"schema": "NS1c2-oracle-summary-v1", "truth": SP.TRUTH_DERIVED, "label": SP.LABEL_ORACLE_CORR,
                       "statement": "PERFECT / ORACLE CORRESPONDENCE (accepted AB1b compute_oracle, read-only): "
                                    "Position and Object Index were used here, and only here, to choose and project the "
                                    "matches; the product holds core row / col and continuous uv_L / uv_R only",
                       "oracle": O.SP.ORACLE, "oracle_config_sha256": O.SP.config_sha256(O.SP.ORACLE),
                       "inputs": inputs, "product_keys": sorted(product),
                       "core_class_counts": {str(kk): int((cls == kk).sum()) for kk in range(4)}, **summ}
            write_json(odir / "oracle-summary.json", summary)
    finally:
        write_json(odir / "correspondence-opened-files.json", guard_record(g))
    return {"correspondences": summary["correspondences"]}


def freeze_correspondence(ctx: Ctx) -> dict:
    sd = ctx.sd()
    require_new_step(ctx, "freeze-correspondence")
    require_action(ctx, "freeze-correspondence")
    need(sd / "correspondence/oracle-correspondences.npz", "perfect-correspondence")
    once(sd / "freeze/correspondence-freeze.json", f"the correspondence freeze of step {ctx.step}")
    cs = require_committed(ctx, "freeze-correspondence")
    import ab1b_geometry as BG
    g = OpenGuard(f"ns1c2-freeze-correspondence-{ctx.step:02d}", [sd / f for f in CORR_FILES], [sd / "freeze"])
    try:
        with g:
            rec = read_json(sd / "correspondence/correspondence-opened-files.json")
            want = {str((sd / f"{SP.OBS_ACQ}/calibration.json").resolve()),
                    str((sd / f"{SP.OBS_AID}/reference-observation.npz").resolve()),
                    str((sd / "freeze/observation-freeze.json").resolve())}
            if (rec["violations"] or set(rec["data_reads"]) != want or rec["modules_loaded"]["cv2"]
                    or rec["modules_loaded"]["fsg_stereo"] or rec["forbidden_reads"]):
                raise SystemExit(f"{PREFIX} STOP the oracle guard record is not clean")
            BG.load_product(sd / "correspondence/oracle-correspondences.npz")
            fz = {"schema": "NS1c2-correspondence-freeze-v1", "truth": SP.TRUTH_DERIVED, "frozen_utc": utc(), "code": cs,
                  "global_step": ctx.step,
                  "statement": "the truth-stripped perfect-correspondence product, frozen before the spherical geometry",
                  "files": {f: sha256(sd / f) for f in CORR_FILES}}
            write_json(sd / "freeze/correspondence-freeze.json", fz)
    finally:
        write_json(sd / "freeze/correspondence-freeze-opened-files.json", guard_record(g))
    return {"files": len(CORR_FILES)}


def truth_reads(events: list[dict]) -> dict:
    paths = [e["path"] for e in events if e.get("event") == "open"]
    ref = [p for p in paths if p.endswith("reference-observation.npz") or p.endswith(".exr") or "/oracle_aid/" in p
           or "evaluation_only" in p]
    return {"position_reads": len(ref), "object_index_reads": len(ref),
            "catalog_reads": len([p for p in paths if "catalog" in p])}


def spherical_geometry(ctx: Ctx) -> dict:
    sd = ctx.sd()
    require_new_step(ctx, "spherical-geometry")
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
    g = OpenGuard(f"ns1c2-geometry-{ctx.step:02d}", [cal, prod_p], [odir])
    try:
        with g:
            inputs = {"calibration": {"path": str(cal), "sha256": sha256(cal)},
                      "correspondences": {"path": str(prod_p), "sha256": sha256(prod_p)}}
            c = read_json(cal)
            FG.validate_calibration(c)
            prod = BG.load_product(prod_p)
            rays = BG.left_core_rays(c)
            r_ = BG.compute_epipolar(c, prod)
            np.savez_compressed(odir / "left-core-rays.npz", **rays)
            np.savez_compressed(odir / "epipolar-result.npz", **r_)
            summary = {"schema": "NS1c2-geometry-summary-v1", "truth": SP.TRUTH_DERIVED, "label": SP.LABEL_GEOMETRY,
                       "statement": "TRUTH-FREE SPHERICAL EPIPOLAR RECONSTRUCTION (accepted AB1b geometry): the "
                                    "calibration and the frozen truth-stripped product only; canonical fixed-head H0",
                       "geometry": BG.SP.GEOMETRY, "geometry_config_sha256": BG.SP.config_sha256(BG.SP.GEOMETRY),
                       "inputs": inputs, "baseline_m": float(c["ipd_m"]), "focal_px": float(c["eyes"][0]["K"][0][0]),
                       **BG.summarize(c, rays, r_)}
            write_json(odir / "geometry-summary.json", summary)
    finally:
        rec = guard_record(g)
        rec.update(truth_reads(rec["events"]))
        write_json(odir / "geometry-opened-files.json", rec)
    return {"triangulated": summary["counts"]["triangulated_epipolar"]}


def freeze_geometry(ctx: Ctx) -> dict:
    sd = ctx.sd()
    require_new_step(ctx, "freeze-geometry")
    require_action(ctx, "freeze-geometry")
    need(sd / "geometry/epipolar-result.npz", "spherical-geometry")
    once(sd / "freeze/geometry-freeze.json", f"the geometry freeze of step {ctx.step}")
    cs = require_committed(ctx, "freeze-geometry")
    cfz = sd / "freeze/correspondence-freeze.json"
    g = OpenGuard(f"ns1c2-freeze-geometry-{ctx.step:02d}", [sd / f for f in GEOM_FILES + CORR_FILES] + [cfz],
                  [sd / "freeze"])
    try:
        with g:
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
            fz = {"schema": "NS1c2-geometry-freeze-v1", "truth": SP.TRUTH_DERIVED, "frozen_utc": utc(), "code": cs,
                  "global_step": ctx.step,
                  "statement": "the truth-free spherical geometry, frozen before any identity is attached",
                  "correspondence_freeze_sha256": sha256(cfz), "files": {f: sha256(sd / f) for f in GEOM_FILES}}
            write_json(sd / "freeze/geometry-freeze.json", fz)
    finally:
        write_json(sd / "freeze/geometry-freeze-opened-files.json", guard_record(g))
    return {"files": len(GEOM_FILES)}


def local_oracle_segmentation(ctx: Ctx) -> dict:
    sd = ctx.sd()
    require_new_step(ctx, "local-oracle-segmentation")
    require_action(ctx, "local-oracle-segmentation")
    need(sd / "freeze/geometry-freeze.json", "freeze-geometry")
    once(sd / "segmentation", f"the local oracle segmentation of step {ctx.step}")
    require_committed(ctx, "local-oracle-segmentation")
    import ns1a_core as NCORE
    odir = sd / "segmentation"
    odir.mkdir(parents=True, exist_ok=True)
    reads = [sd / "freeze/geometry-freeze.json"] + [sd / f for f in GEOM_FILES] + [
        sd / "correspondence/oracle-correspondences.npz", sd / f"{SP.OBS_AID}/reference-observation.npz"]
    g = OpenGuard(f"ns1c2-segmentation-{ctx.step:02d}", reads, [odir])
    try:
        with g:
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
            summ = {"schema": "NS1c2-identity-summary-v1", "truth": SP.TRUTH_DERIVED, "label": SP.LABEL_SEGMENTATION,
                    "statement": "ORACLE SEGMENTATION AID: temporary_entity_id = the left raw-core Object Index at the "
                                 "exact uv_L centre of each valid correspondence; not natural identity; no catalog, no "
                                 "names", "reference_members_read": list(SP.SEGMENTATION_MEMBERS),
                    **NCORE.identity_summary(ids)}
            write_json(odir / "identity-summary.json", summ)
    finally:
        write_json(odir / "segmentation-opened-files.json", guard_record(g, {"reference_members_read":
                                                                              list(SP.SEGMENTATION_MEMBERS)}))
    return {"entities": len(summ["entities"])}


# ------------------------------------------------------------------ target-only H0 fusion (prefix: recomputed from NS1c)
FUSION_FIELDS = ("action", "map_before", "map_after", "measured_points", "matched", "new", "affected_surfels",
                 "matched_distance_m", "patch_id", "target")


def fuse(ctx: Ctx) -> dict:
    run, sd, k = ctx.run, ctx.sd(), int(ctx.step)
    d = require_action(ctx, "fuse")
    prefix = SP.is_prefix(k)
    if prefix:
        need(sd / "replay/replay.json", "replay")
    else:
        need(sd / "segmentation/identity-summary.json", "local-oracle-segmentation")
    once(sd / "fusion/fusion.json", f"the H0 fusion of step {k}")
    cs = require_committed(ctx, "fuse")
    import ns1b_core as B
    import ns1c2_core as CORE
    from fov3d.reconstruction import surface_map as SMOD  # noqa: F401
    target = int(d["action"]["target"])
    prev = read_json(run / prev_scene_rel(k))
    mrec = prev["entities"][str(target)]["map"]
    root, ref_root = obs_root(ctx)
    reads = [root / "freeze/geometry-freeze.json"] + [root / f for f in GEOM_FILES + SEG_FILES] + [
        root / "correspondence/oracle-correspondences.npz", root / f"{SP.OBS_ACQ}/rgb-observation.npz",
        sd / "plan/decision.json", run / prev_scene_rel(k), res(mrec["path"], run)]
    if prefix:
        reads += [ns1c("manifest.json"), root / "freeze/correspondence-freeze.json",
                  root / "freeze/observation-freeze.json", root / "fusion/fusion.json",
                  root / "fusion/fused-target-map.npz", sd / "replay/replay.json"]
    else:
        reads += [root / "segmentation/segmentation-opened-files.json"]
    (sd / "fusion").mkdir(parents=True, exist_ok=True)
    g = OpenGuard(f"ns1c2-fuse-{k:02d}", reads, [sd / "fusion"])
    pg = process_guard(ctx)
    failure = None
    try:
        with g, pg:
            verify_record_hashes(root, "freeze/geometry-freeze.json")
            if prefix:   # only the files this stage consumes (the full freezes were verified by `replay`)
                cfz = read_json(root / "freeze/correspondence-freeze.json")
                ofz = read_json(root / "freeze/observation-freeze.json")
                prod_rel, rgb_rel = "correspondence/oracle-correspondences.npz", f"{SP.OBS_ACQ}/rgb-observation.npz"
                if sha256(root / prod_rel) != cfz["files"][prod_rel] or sha256(root / rgb_rel) != ofz["files"][rgb_rel]:
                    raise SystemExit(f"{PREFIX} STOP the NS1c correspondence product / RGB observation changed")
                ns1c_verify([f"{SP.step_dir(k)}/{r}" for r in SEG_FILES + ("fusion/fusion.json",
                                                                           "fusion/fused-target-map.npz",
                                                                           "freeze/correspondence-freeze.json",
                                                                           "freeze/observation-freeze.json",
                                                                           prod_rel, rgb_rel)])
            if sha256(res(mrec["path"], run)) != mrec["sha256"]:
                raise SystemExit(f"{PREFIX} STOP the target map changed since the scene state")
            prod = load_npz(root / "correspondence/oracle-correspondences.npz")
            r_ = read_members(root / "geometry/epipolar-result.npz", ("P_epi", "valid_epi"))
            idn = load_npz(root / "segmentation/local-identity.npz")
            rgb_l = read_members(root / f"{SP.OBS_ACQ}/rgb-observation.npz", ("rgb_L",))["rgb_L"]
            if not (np.array_equal(idn["left_core_row"], prod["left_core_row"])
                    and np.array_equal(idn["valid"], r_["valid_epi"])):
                raise SystemExit(f"{PREFIX} STOP identity, product and geometry are not aligned")
            uv = prod["uv_L"].astype(np.int64)
            rgb = rgb_l[uv[:, 1], uv[:, 0]].astype(np.float64)
            patch = CORE.target_patch(r_["P_epi"], r_["valid_epi"], idn["temporary_entity_id"], rgb, target, k)
            sm = CORE.load_map(res(mrec["path"], run))
            if patch["patch_id"] in sm.patch_ids:
                raise SystemExit(f"{PREFIX} STOP the patch id {patch['patch_id']} is already in the target map")
            fused, rec = B.fuse_h0(sm, patch, target)
            np.savez_compressed(sd / "fusion/target-patch.npz", xyz_h=patch["xyz_h"], rgb=patch["rgb"],
                                instance_id=patch["instance_id"])
            np.savez_compressed(sd / "fusion/fused-target-map.npz", **B.map_arrays(fused))
            idsum = read_json(root / "segmentation/identity-summary.json")
            incidental = sorted(int(e) for e in idsum["entities"] if int(e) != target)
            out = {"schema": "NS1c2-fusion-v1", "truth": SP.TRUTH_DERIVED, "code": cs, "global_step": k,
                   "prefix": prefix, "observation_source": ref_root,
                   "statement": "the selected target's points of the frozen spherical measurement, fused into ONLY that "
                                "target's H0 map with the accepted surface map (12 mm / 12 mm) in canonical H0, with one "
                                "exact replay; incidental ids in view are never fused",
                   "target": target, "patch_id": patch["patch_id"], "map_before_path": mrec["path"],
                   "map_before_sha256": mrec["sha256"], "valid_correspondences":
                       int(np.asarray(r_["valid_epi"], bool).sum()), "entities_in_view": idsum["entities"],
                   "incidental_ids_not_fused": incidental, "local_gaze_deg": d["action"]["local_gaze_deg"],
                   "world_gaze_deg": d["action"]["world_gaze_deg"], **rec}
            if prefix:
                nf = read_json(root / "fusion/fusion.json")
                same_map = CORE.maps_equal(B.map_arrays(fused), load_npz(root / "fusion/fused-target-map.npz"))
                diffs = {f: [CORE.jsonable(out.get(f)), nf.get(f)] for f in FUSION_FIELDS
                         if CORE.jsonable(out.get(f)) != nf.get(f)}
                out["ns1c_prefix_comparison"] = {"ns1c_fusion": f"{ref_root}/fusion/fusion.json",
                                                 "fused_map_bitwise_equal": same_map, "field_differences": diffs,
                                                 "equal": same_map and not diffs}
                if not out["ns1c_prefix_comparison"]["equal"]:
                    failure = f"prefix step {k}: the recomputed fusion differs from NS1c's ({diffs}, map {same_map})"
            write_json(sd / "fusion/fusion.json", out)
    finally:
        write_json(sd / "fusion/fusion-opened-files.json", guard_record(g, {"process_guard": process_record(pg)}))
    if failure:
        raise SystemExit(f"{PREFIX} STOP {failure} (Outcome 4)")
    return {kk: out[kk] for kk in ("action", "target", "map_before", "measured_points", "matched", "new", "map_after")}


# ------------------------------------------------------------------ update: context, re-probe, the adapter's commit
def update(ctx: Ctx) -> dict:
    run, sd, k = ctx.run, ctx.sd(), int(ctx.step)
    d = require_action(ctx, "update")
    need(sd / "fusion/fusion.json", "fuse")
    once(sd / "update/update.json", f"the update of step {k}")
    cs = require_committed(ctx, "update")
    prefix = SP.is_prefix(k)
    import ns1b_chart as CH
    import ns1b_core as B
    import ns1c2_core as CORE
    import ns1c2_phase as PH
    from fov3d.control import controller02 as c2, integrated as ic
    CH.ensure_policy_modules()
    import ns1a_core  # noqa: F401
    import fsg6f_frontier  # noqa: F401
    prev = read_json(run / prev_scene_rel(k))
    t = int(d["action"]["target"])
    rec_t = prev["entities"][str(t)]
    root, ref_root = obs_root(ctx)
    reads = probe_reads(run, prev["entities"]) + [
        run / prev_scene_rel(k), run / "charts/policy-charts.json", sd / "plan/decision.json",
        sd / "fusion/fusion.json", sd / "fusion/fused-target-map.npz", root / "freeze/observation-freeze.json",
        root / f"{SP.OBS_ACQ}/calibration.json", root / f"{SP.OBS_ACQ}/rgb-observation.npz",
        root / f"{SP.OBS_AID}/reference-observation.npz"]
    ns1c_cmp = [f"{SP.step_dir(k)}/update/controller-state.npz", f"{SP.step_dir(k)}/update/evidence.npz",
                f"{SP.step_dir(k)}/update/probes/e{SP.CONTINUING:05d}.json", f"scene/state-after-step-{k:02d}.json"]
    if prefix:
        reads += [ns1c("manifest.json")] + [ns1c(r) for r in ns1c_cmp]
    (sd / "update/probes").mkdir(parents=True, exist_ok=True)
    g = OpenGuard(f"ns1c2-update-{k:02d}", reads, [sd / "update", run / "scene", run / "freeze"])
    pg = process_guard(ctx)
    failure = None
    try:
        with g, pg, PH.GateGuard(d["phase_after_decide"], f"update step {k}") as gg:
            fz = read_json(root / "freeze/observation-freeze.json")
            for rel in (f"{SP.OBS_ACQ}/calibration.json", f"{SP.OBS_ACQ}/rgb-observation.npz",
                        f"{SP.OBS_AID}/reference-observation.npz"):
                if sha256(root / rel) != fz["files"][rel]:
                    raise SystemExit(f"{PREFIX} STOP {rel} changed after the observation freeze")
            chs = read_json(run / "charts/policy-charts.json")["charts"]
            r = np.asarray(chs[str(t)]["R_HC"], np.float64)
            fu = read_json(sd / "fusion/fusion.json")
            # -- the target's controller observation state and context (Controller-01 observe order)
            cal1 = read_json(root / f"{SP.OBS_ACQ}/calibration.json")
            rec1, meta1, st1 = B.matcher_state(cal1, load_npz(root / f"{SP.OBS_ACQ}/rgb-observation.npz"),
                                               load_npz(root / f"{SP.OBS_AID}/reference-observation.npz"))
            state_file(sd / "update/controller-state.npz", st1, rec1["valid"])
            c_ctx = CORE.context_from_record(rec_t, run)
            ad = B.add_look(c_ctx, cal1, st1, rec1["valid"], r, tuple(d["action"]["local_gaze_deg"]))
            ev = B.evidence_arrays(c_ctx)
            np.savez_compressed(sd / "update/evidence.npz", **ev)
            new = json.loads(json.dumps(rec_t))
            new["looks"].append({"source": f"{'NS1c (replayed)' if prefix else 'NS1c2'} step {k:02d} ({SP.patch_id(k)})",
                                 "calibration": f"{ref_root}/{SP.OBS_ACQ}/calibration.json",
                                 "calibration_sha256": sha256(root / f"{SP.OBS_ACQ}/calibration.json"),
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
            new["revision"] = CORE.revision(new)
            if len(c_ctx.history) != new["own_looks"]:
                raise SystemExit(f"{PREFIX} STOP the context history does not match the own-look count")
            ents = {kk: json.loads(json.dumps(v)) for kk, v in prev["entities"].items()}
            ents[str(t)] = new
            # -- the accepted Controller-02 commit: fixations, refresh (fresh probe when the revision changed), events
            m = PH.SceneMachine.from_json(d["machine_after_decide"])
            plan = plan_from_json(d["plan"])
            written, outs = {}, {}

            def probe(i):
                rec = ents[str(i)]
                out = CORE.probe_entity(rec, run, chs[str(i)], f"NORMAL re-probe of entity {i} (step {k})")
                pth = sd / f"update/probes/e{i:05d}.json"
                write_json(pth, probe_file_record(i, f"step-{k:02d}", rec["revision"], out,
                                                  {"executed": False}))
                written[i] = {"path": f"run:{SP.step_dir(k)}/update/probes/e{i:05d}.json", "sha256": sha256(pth),
                              "revision": rec["revision"], "provenance": "fresh", "computed_at": f"step-{k:02d}"}
                outs[i] = out
                return CORE.probe_result(out, i, {"probe_path": written[i]["path"], "revision": rec["revision"]})
            n_ev = len(m.events)
            outcome = ic.ObservationOutcome(initialized=None, record={
                "fusion": fu["action"], "map_before": fu["map_before"], "map_after": fu["map_after"],
                "measured_points": fu["measured_points"], "matched": fu["matched"], "new": fu["new"],
                "observation_source": ref_root})
            record = m.commit(plan, outcome, probe, lambda i: CORE.revision(ents[str(i)]))
            events = m.events[n_ev:]
            if t not in written:
                raise SystemExit(f"{PREFIX} STOP the target's revision did not change (no fresh probe)")
            for kk in ents:
                i = int(kk)
                if i in written:
                    ents[kk]["probe"] = written[i]
                    ents[kk] = with_status(ents[kk], m.statuses[i], outs[i])
                else:
                    ents[kk]["probe"] = {**prev["entities"][kk]["probe"], "provenance": "cached"}
                    ents[kk] = with_status(ents[kk], m.statuses[i])
            out_t = outs[t]
            if out_t["adapter"]["calls"]["P3"] != 0 or any(o["adapter"]["calls"]["P3"] for o in outs.values()):
                failure = "P3 (the gate's predicted calibration) was called by a NORMAL probe"
            executed_before = int(prev["executed_actions"])
            new_actions = int(prev["new_actions"]) + (0 if prefix else 1)
            stop = (not prefix) and plan["kind"] == "attend" and CORE.stop_event(t, fu["action"])
            cmp_ = None
            if prefix:
                ns1c_verify(ns1c_cmp)
                n_after = read_json(ns1c(f"scene/state-after-step-{k:02d}.json"))["entities"][str(SP.CONTINUING)]
                nprobe = read_json(ns1c(f"{SP.step_dir(k)}/update/probes/e{SP.CONTINUING:05d}.json"))["probe"]
                pol = CORE.policy_comparison(nprobe, out_t)
                cmp_ = {"controller_state_equal": arrays_equal(load_npz(sd / "update/controller-state.npz"),
                                                               load_npz(ns1c(ns1c_cmp[0]))),
                        "evidence_equal": arrays_equal(ev, load_npz(ns1c(ns1c_cmp[1]))),
                        "probe_policy_differences": pol[:5], "probe_policy_equal": not pol,
                        "own_looks": [new["own_looks"], n_after["own_looks"]],
                        "visited": [new["visited"], n_after["visited"]],
                        "current_local_gaze": [new["current_local_gaze"], n_after["current_local_gaze"]],
                        "revision": [new["revision"], n_after["revision"]],
                        "map_surfels": [new["map"]["surfels"], n_after["map"]["surfels"]],
                        "history_calibrations": [[lk["calibration_sha256"] for lk in new["looks"]],
                                                 [lk["calibration_sha256"] for lk in n_after["looks"]]],
                        "ns1c_gate_record_ignored": {"admissible": nprobe["gate"]["admissible"],
                                                     "reason": nprobe["gate"]["reason"]}}
                cmp_["equal"] = bool(cmp_["controller_state_equal"] and cmp_["evidence_equal"] and not pol
                                     and all(a == b for a, b in (cmp_[f] for f in (
                                         "own_looks", "visited", "current_local_gaze", "revision", "map_surfels",
                                         "history_calibrations"))))
                if not cmp_["equal"]:
                    failure = f"prefix step {k}: the replayed update differs from NS1c {cmp_}"
            scene = {"schema": "NS1c2-scene-state-v1", "truth": SP.TRUTH_DERIVED, "label": f"after-step-{k:02d}",
                     "global_step": k, "prefix": prefix, "code": cs, "phase": m.phase.value, "current": t,
                     "previous": prev["current"], "attention_bout": int(record["attention_bout"]),
                     "executed_actions": executed_before + 1, "new_actions": new_actions, "budget": prev["budget"],
                     "cap": prev.get("cap"), "scene_ids": prev["scene_ids"], "coherent_ids": prev["coherent_ids"],
                     "deferred": prev["deferred"], "entities": ents,
                     "events": d.get("events_in_decide", []) + events, "machine": m.to_json(),
                     "stopped": bool(stop), "stop": None, "gate_guard": gg.record(),
                     "last_decision": {"global_step": k, "kind": d["kind"], "phase": d["action"]["phase"],
                                       "scheduler_decision": d["scheduler_decision"],
                                       "scheduler_reason": d["scheduler_reason"], "attention_bout": d["attention_bout"],
                                       "previous_target": d.get("previous_target"),
                                       "target_transition": d.get("target_transition")},
                     "last_action": {"global_step": k, "target": t, "source": d["action"]["source"],
                                     "local_gaze_deg": d["action"]["local_gaze_deg"],
                                     "world_gaze_deg": d["action"]["world_gaze_deg"], "fusion": fu["action"],
                                     "patch_id": fu["patch_id"], "observation_source": ref_root},
                     "machine_action_record": CORE.jsonable({kk: v for kk, v in record.items()
                                                             if kk not in ("vergence", "focus")}),
                     "table": scene_table(ents)}
            if stop:
                scene["stop"] = {"global_step": k, "event": "FIRST EXECUTED NORMAL ACTION ON A TARGET OTHER THAN 172",
                                 "from": prev["current"], "to": t, "scheduler_reason": d["scheduler_reason"],
                                 "fusion": fu["action"], "status_172_at_switch":
                                     prev["entities"][str(SP.CONTINUING)]["status"],
                                 "post_action_probe_of_new_target": {"path": ents[str(t)]["probe"]["path"],
                                                                     "label": ents[str(t)]["status"]["label"],
                                                                     "proposal": ents[str(t)].get("proposal"),
                                                                     "executed": False},
                                 "statement": "the canonical stop: one read-only post-action probe of the new target; "
                                              "the scene status table recomputed once; the scene state frozen; no "
                                              "further action is scheduled"}
            rel = SP.scene_state_rel(f"after-step-{k:02d}")
            write_json(run / rel, scene)
            upd = {"schema": "NS1c2-update-v1", "truth": SP.TRUTH_DERIVED, "code": cs, "global_step": k, "target": t,
                   "prefix": prefix, "observation_source": ref_root,
                   "statement": "the target's controller observation state and context updated in Controller-01 observe "
                                "order; the adapter's Controller-02 commit (fixations, refresh with the deferral rule, "
                                "events), with a fresh NORMAL probe wherever the revision changed and the cache elsewhere",
                   "matcher": CORE.jsonable(meta1),
                   "controller_state_target_support": int((np.asarray(rec1["valid"], bool)
                                                           & (np.asarray(rec1["instance_id"]) == t)).sum()),
                   "controller_state_target_pixels_L": int((st1["ids_left"] == t).sum()),
                   "north_star_target_points": int(fu["measured_points"]), "evidence_adapter": ad,
                   "evidence_cells": {n: int(v.sum()) for n, v in ev.items()}, "own_looks": new["own_looks"],
                   "visited": new["visited"], "fresh_probes": sorted(written), "status_after": ents[str(t)]["status"],
                   "events": events, "stop": scene["stop"], "ns1c_prefix_comparison": cmp_,
                   "gate_guard": gg.record(), "scene_state": {"path": rel, "sha256": sha256(run / rel)}}
            write_json(sd / "update/update.json", upd)
            if stop:
                write_json(run / "scene/final-scene-state.json", {**scene, "label": "final"})
                files = sorted(str(p.relative_to(run)) for p in (run / "scene").glob("*.json"))
                write_json(run / "freeze/scene-freeze.json", {
                    "schema": "NS1c2-scene-freeze-v1", "truth": SP.TRUTH_DERIVED, "frozen_utc": utc(), "code": cs,
                    "statement": "the scene state frozen after the first executed NORMAL action on a target other than "
                                 "172; NS1c2 stops here", "stop": scene["stop"],
                    "files": {f: sha256(run / f) for f in files}})
    finally:
        write_json(sd / "update/update-opened-files.json", guard_record(g, {"process_guard": process_record(pg)}))
    if failure:
        raise SystemExit(f"{PREFIX} STOP {failure} (Outcome 4)")
    return {"target": t, "status_after": ents[str(t)]["status"]["label"], "proposal": ents[str(t)].get("proposal"),
            "fresh": sorted(written), "stop": bool(stop), "events": [[e["event"], e["object"]] for e in events]}


# ------------------------------------------------------------------ the first true divergence (frozen before any render)
def divergence(ctx: Ctx) -> dict:
    run = ctx.run
    k3 = SP.PREFIX_STEPS - 1
    need(run / SP.scene_state_rel(f"after-step-{k3:02d}"), "the replayed prefix")
    once(run / "divergence/divergence.json", "the divergence record")
    if (run / SP.step_dir(SP.PREFIX_STEPS)).exists():
        raise Refused(f"{PREFIX} REFUSED the divergence is frozen before step {SP.PREFIX_STEPS} exists")
    cs = require_committed(ctx, "divergence")
    import ns1c2_core as CORE
    import ns1c2_phase as PH
    from fov3d.control import controller02 as c2
    st = read_json(run / SP.scene_state_rel(f"after-step-{k3:02d}"))
    rec = st["entities"][str(SP.CONTINUING)]
    ns1c_rels = [f"{SP.step_dir(k3)}/update/probes/e{SP.CONTINUING:05d}.json", f"scene/state-after-step-{k3:02d}.json",
                 SP.NS1C_STEP4_DECISION]
    reads = [run / SP.scene_state_rel(f"after-step-{k3:02d}"), res(rec["probe"]["path"], run),
             run / "charts/policy-charts.json", ns1c("manifest.json")] + [ns1c(r) for r in ns1c_rels]
    (run / "divergence").mkdir(parents=True, exist_ok=True)
    g = OpenGuard("ns1c2-divergence", reads, [run / "divergence", run / "freeze"])
    problems = []
    try:
        with g, PH.GateGuard(st["phase"], "divergence") as gg:
            ns1c_verify(ns1c_rels)
            pf = read_json(res(rec["probe"]["path"], run))
            mine = pf["probe"]
            nprobe = read_json(ns1c(ns1c_rels[0]))["probe"]
            n172 = read_json(ns1c(ns1c_rels[1]))["entities"][str(SP.CONTINUING)]
            n4 = read_json(ns1c(ns1c_rels[2]))
            pol = CORE.policy_comparison(nprobe, mine)
            m = PH.SceneMachine.from_json(st["machine"])
            status = m.statuses[SP.CONTINUING]
            dry = PH.SceneMachine.from_json(json.loads(json.dumps(m.to_json())))
            sched = c2.schedule_normal(dry.current, dry.statuses.values())

            def no_gate(i, proposal):
                raise PH.GateOutsideResidue("the divergence dry run never consults the gate")
            plan = dry.decide(no_gate)
            budget = int(st["budget"])
            cap = CORE.derived_cap(budget, int(rec["own_looks"]))
            p = mine["proposal"] or {}
            ns = mine["summary"]
            row = {"entity": SP.CONTINUING, "own_looks": rec["own_looks"], "map_surfels": rec["map"]["surfels"],
                   "revision": rec["revision"], "chart_id": rec["chart_id"], "chart_sha256": rec["chart_sha256"],
                   "current_local_gaze": rec["current_local_gaze"], "fsg6f": ns["fsg6f"], "cyclopean": ns.get("cyclopean"),
                   "proposal": {k_: p.get(k_) for k_ in ("source", "local_gaze_deg", "world_gaze_deg", "leverage",
                                                         "angle_from_seed_deg")} if p else None,
                   "local_state": status.local.value, "disposition": status.disposition.value, "label": status.label,
                   "gate_calls": gg.record()["calls"], "probe_P3_calls": mine["adapter"]["calls"]["P3"]}
            comparison = {
                "NS1c": {"fsg6f": nprobe["summary"]["fsg6f"]["reason"],
                         "cyclopean": (nprobe["summary"].get("cyclopean") or {}).get("reason"),
                         "cyclopean_proposal_local": (nprobe["proposal"] or {}).get("local_gaze_deg"),
                         "final_gate": "CALLED (in NORMAL service)",
                         "gate_verdict": {"admissible": nprobe["gate"]["admissible"], "reason": nprobe["gate"]["reason"]},
                         "service_state": n172["service"]["label"],
                         "scheduler": {"reason": n4["scheduler_decision"]["reason"],
                                       "target": n4["scheduler_decision"]["target_id"]}},
                "NS1c2": {"fsg6f": ns["fsg6f"]["reason"], "cyclopean": (ns.get("cyclopean") or {}).get("reason"),
                          "cyclopean_proposal_local": p.get("local_gaze_deg"), "final_gate": "NOT CALLED",
                          "gate_calls": gg.record()["calls"], "service_state": status.label,
                          "scheduler": None if sched is None else {"reason": sched.reason, "target": sched.target_id}},
                "policy_part_equal": not pol, "policy_differences": pol[:5]}
            if pol:
                problems.append(f"the post-step-3 probe differs from NS1c's: {pol[:3]}")
            if p.get("source") is None:
                problems.append("the corrected probe carries no action")
            if status.local.value != "ACTIONABLE" or status.disposition.value != "NORMAL":
                problems.append(f"172 is not NORMAL ACTIONABLE ({status.label})")
            if sched is None or sched.reason != "retain" or int(sched.target_id) != SP.CONTINUING or \
                    plan["kind"] != "attend" or int(plan["target_id"]) != SP.CONTINUING:
                problems.append("the scheduler would not retain 172 before executing its proposal")
            if gg.record()["calls"] != 0 or mine["adapter"]["calls"]["P3"] != 0:
                problems.append("a gate call occurred in NORMAL")
            if cap != SP.CAP_EXPECTED:
                problems.append(f"the derived cap {cap} != {SP.CAP_EXPECTED}")
            out = {"schema": "NS1c2-divergence-v1", "truth": SP.TRUTH_DERIVED, "code": cs,
                   "label": "THE FIRST TRUE DIVERGENCE FROM NS1c",
                   "statement": "the reconstructed post-step-3 state: 172's ungated NORMAL probe, its Controller-02 "
                                "status and the accepted scheduler decision, frozen before any NS1c2 render; NS1c gated "
                                "the same proposal in NORMAL service",
                   "state": row, "scheduler_decision": None if sched is None else {
                       "function": "controller02.schedule_normal", "kind": sched.kind, "target_id": sched.target_id,
                       "reason": sched.reason, "current_before": dry.current if False else st["current"]},
                   "planned_action": {"target": plan.get("target_id"), "source": plan["action"].source if plan.get(
                       "action") else None, "local_gaze_deg": list(plan["action"].gaze_yaw_pitch_deg)
                       if plan.get("action") else None},
                   "comparison": comparison, "budget": budget, "own_looks_172": rec["own_looks"],
                   "cap": cap, "cap_formula": "MAX_NEW_POST_DIVERGENCE_ACTIONS = (ordinary_budget - own_looks_172) + 1",
                   "cap_expected": SP.CAP_EXPECTED, "gate_guard": gg.record(),
                   "table": st["table"], "problems": problems, "ok": not problems}
            write_json(run / "divergence/divergence.json", out)
            write_json(run / "freeze/divergence-freeze.json", {
                "schema": "NS1c2-divergence-freeze-v1", "truth": SP.TRUTH_DERIVED, "frozen_utc": utc(), "code": cs,
                "statement": "the divergence record and the derived cap, frozen before any NS1c2 render",
                "files": {"divergence/divergence.json": sha256(run / "divergence/divergence.json")}})
    finally:
        write_json(run / "divergence/divergence-opened-files.json", guard_record(g))
    if problems:
        raise SystemExit(f"{PREFIX} STOP the divergence (no render): {problems}")
    return {"state": row["label"], "proposal": row["proposal"], "scheduler": comparison["NS1c2"]["scheduler"],
            "cap": cap}


# ------------------------------------------------------------------ the drivers
def stage_cmd(ctx: Ctx, stage: str, step: int) -> list[str]:
    cmd = [sys.executable, str(HERE / "ns1c2_run.py"), stage, "--run", str(ctx.run), "--step", str(step)]
    if ctx.dev:
        cmd.append("--dev")
    if stage in ("acquire", "preflight") and ctx.rehearsal_spp is not None:
        cmd += ["--rehearsal-spp", str(int(ctx.rehearsal_spp))]
    return cmd


def run_step(ctx: Ctx, k: int, stages) -> dict:
    for stage in stages:
        p = subprocess.run(stage_cmd(ctx, stage, k), cwd=REPO)
        if p.returncode != 0:
            raise SystemExit(f"{PREFIX} STOP stage {stage} of step {k} exited {p.returncode}")
        if stage == "schedule":
            d = read_json(ctx.run / SP.step_dir(k) / "plan/decision.json")
            if d["kind"] not in ("attend", "final_residue"):
                return d
    return read_json(ctx.run / SP.step_dir(k) / "plan/decision.json")


def prefix(ctx: Ctx) -> dict:
    run = ctx.run
    need(run / SP.scene_state_rel("initial"), "initial-probe")
    if (run / SP.step_dir(0)).exists():
        raise Refused(f"{PREFIX} REFUSED the prefix replay has started already")
    require_committed(ctx, "prefix")
    t0 = time.time()
    steps = []
    for k in range(SP.PREFIX_STEPS):
        ts = time.time()
        d = run_step(ctx, k, SP.PREFIX_STAGES)
        if d["kind"] != "attend":
            raise SystemExit(f"{PREFIX} STOP prefix step {k} is not an ordinary action ({d['kind']})")
        steps.append({"step": k, "target": d["action"]["target"], "reason": d["scheduler_reason"],
                      "seconds": round(time.time() - ts, 1)})
        print(f"{PREFIX} prefix step {k} replayed: target {d['action']['target']} ({d['scheduler_reason']}) "
              f"{steps[-1]['seconds']} s", flush=True)
    return {"steps": steps, "seconds": round(time.time() - t0, 1)}


def loop(ctx: Ctx, max_steps: int | None = None) -> dict:
    run = ctx.run
    need(run / "freeze/divergence-freeze.json", "divergence")
    if (run / "scene/final-scene-state.json").exists() or (run / "scene/terminal.json").exists():
        raise Refused(f"{PREFIX} REFUSED the run has stopped (final scene state or terminal record exists)")
    require_committed(ctx, "loop")
    cap = int(read_json(run / "divergence/divergence.json")["cap"])
    t0 = time.time()
    steps, durations = [], []
    _rel, sc = latest_scene(run)
    k = int(sc["global_step"]) + 1
    if k < SP.PREFIX_STEPS:
        raise Refused(f"{PREFIX} REFUSED the prefix is not complete")
    while True:
        if (run / "scene/final-scene-state.json").exists() or (run / "scene/terminal.json").exists():
            break
        if max_steps is not None and len(steps) >= max_steps:
            break
        ts = time.time()
        d = run_step(ctx, k, SP.STEP)
        dt_s = time.time() - ts
        if d["kind"] not in ("attend", "final_residue"):
            steps.append({"step": k, "kind": d["kind"], "seconds": round(dt_s, 1)})
            break
        durations.append(dt_s)
        sc = read_json(run / SP.scene_state_rel(f"after-step-{k:02d}"))
        t = sc["entities"][str(d["action"]["target"])]
        steps.append({"step": k, "target": d["action"]["target"], "reason": d["scheduler_reason"],
                      "phase": d["action"]["phase"], "source": d["action"]["source"], "seconds": round(dt_s, 1),
                      "status_after": t["status"]["label"], "stopped": sc["stopped"]})
        print(f"{PREFIX} loop step {k}: target {d['action']['target']} ({d['scheduler_reason']}, "
              f"{d['action']['source']}) {dt_s:.1f} s; after {t['status']['label']}; stopped {sc['stopped']}",
              flush=True)
        if sc["stopped"]:
            break
        mean = float(np.mean(durations))
        projected = (time.time() - t0) + (cap - int(sc["new_actions"])) * mean
        if projected > SP.STEP_BUDGET_PROJECTION_S:
            write_json(run / f"loop/budget-stop-after-step-{k:02d}.json", {
                "schema": "NS1c2-budget-stop-v1", "step": k, "mean_step_seconds": mean, "projected_seconds": projected,
                "budget_seconds": SP.STEP_BUDGET_PROJECTION_S, "statement": "STOP before the next step (contract "
                                                                           "section 19); continuation only by Luiz"})
            raise SystemExit(f"{PREFIX} STOP the time projection {projected:.0f} s exceeds "
                             f"{SP.STEP_BUDGET_PROJECTION_S:.0f} s after step {k}")
        k += 1
    return {"steps": steps, "seconds": round(time.time() - t0, 1),
            "final": (run / "scene/final-scene-state.json").exists(), "terminal": (run / "scene/terminal.json").exists()}


# ------------------------------------------------------------------ visuals and manifest
def visualize(ctx: Ctx, vis: Path) -> dict:
    run = ctx.run
    need(run / SP.scene_state_rel("initial"), "initial-probe")
    import ns1c2_visuals as V
    man = V.visualize(run, vis)
    write_manifest(run)
    return {k: v["sha256"] for k, v in man["figures"].items()}


def write_manifest(run: Path) -> dict:
    files = sorted(str(p.relative_to(run)) for p in run.rglob("*") if p.is_file()
                   and p.name not in ("manifest.json", "check-summary.json", "process-log.jsonl"))
    m = {"schema": "NS1c2-manifest-v1", "experiment": SP.EXPERIMENT, "contract": SP.CONTRACT, "code": code_state(),
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
    ap.add_argument("--dev-scene", default=None, help="eligibility --dev only: the rehearsal scene ids, e.g. 172,10,110,178")
    ap.add_argument("--rehearsal-spp", type=int, default=None, help="loop / preflight / acquire --dev only")
    ap.add_argument("--max-steps", type=int, default=None, help="loop --dev only: stop the rehearsal loop early")
    a = ap.parse_args(argv)
    if (a.command in SP.STEP_STAGES) != (a.step is not None):
        raise SystemExit(f"{PREFIX} --step is required by, and only by, the step stages")
    if a.dev_scene is not None and (a.command != "eligibility" or not a.dev):
        raise SystemExit(f"{PREFIX} --dev-scene is an `eligibility --dev` option only")
    if a.rehearsal_spp is not None and (a.command not in ("loop", "acquire", "preflight") or not a.dev):
        raise SystemExit(f"{PREFIX} --rehearsal-spp is a `loop --dev` / `acquire --dev` option only")
    if a.max_steps is not None and (a.command != "loop" or not a.dev):
        raise SystemExit(f"{PREFIX} --max-steps is a `loop --dev` option only")
    scene = [int(x) for x in a.dev_scene.split(",")] if a.dev_scene else None
    ctx = Ctx(a.run, a.dev, a.step, scene, a.rehearsal_spp)
    t0 = time.time()
    fns = {"source": source, "synthetic": synthetic, "known-answer": known_answer, "eligibility": eligibility,
           "charts": charts, "contexts": contexts, "initial-probe": initial_probe, "schedule": schedule,
           "replay": replay, "preflight": preflight, "acquire": acquire, "freeze-observation": freeze_observation,
           "perfect-correspondence": perfect_correspondence, "freeze-correspondence": freeze_correspondence,
           "spherical-geometry": spherical_geometry, "freeze-geometry": freeze_geometry,
           "local-oracle-segmentation": local_oracle_segmentation, "fuse": fuse, "update": update,
           "prefix": prefix, "divergence": divergence, "loop": lambda c: loop(c, a.max_steps),
           "visualize": lambda c: visualize(c, a.visuals or SP.VIS_DEFAULT)}
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
