"""North Star-1c: coherent multi-entity control, first scene switch (run order, truth boundary, process contract).

Contract: docs/north-star/ns1c-coherent-first-scene-switch-contract.md.

    .venv/bin/python tools/north_star/ns1c_run.py source         --run RUN
    .venv/bin/python tools/north_star/ns1c_run.py synthetic      --run RUN
    .venv/bin/python tools/north_star/ns1c_run.py eligibility    --run RUN
    .venv/bin/python tools/north_star/ns1c_run.py charts         --run RUN
    .venv/bin/python tools/north_star/ns1c_run.py contexts       --run RUN
    .venv/bin/python tools/north_star/ns1c_run.py initial-probe  --run RUN
    .venv/bin/python tools/north_star/ns1c_run.py loop           --run RUN    # the step stages, step after step
    .venv/bin/python tools/north_star/ns1c_run.py visualize      --run RUN --visuals VIS

    step stages (each once per global step k; normally launched by ``loop``):
    schedule | preflight | acquire | freeze-observation | perfect-correspondence | freeze-correspondence |
    spherical-geometry | freeze-geometry | local-oracle-segmentation | fuse | update      --run RUN --step k

Every canonical stage runs once (per step for the step stages), from a clean pushed commit, under the accepted
``nb1a_guard.OpenGuard`` allowlist (except ``synthetic``, which reads no run data).  No stage opens a catalog, an object
name, the Controller-01 run, an evaluation file or future visibility.  ``--dev`` runs on a scratch development run (never
the canonical RUN) from a dirty tree; ``eligibility --dev --dev-scene 172,10,110,178`` sets the rehearsal scene;
``loop --dev --rehearsal-spp N`` renders the synthetic factory-startup rehearsal instead of Classroom.
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
for _p in (HERE, HERE.parent, HERE.parent / "active_bootstrap", HERE.parent / "natural_bootstrap", REPO):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import ns1c_spec as SP  # noqa: E402
from nb1a_guard import OpenGuard  # noqa: E402  (accepted, read-only)

PREFIX = "[ns1c]"
TRUTH_CLASSES = {
    "ORACLE INPUT": "the saved NS1a initialization looks, the accepted NS1b look and the new rendered observations; the "
                    "ORACLE AID (Position, Object Index) used by the perfect correspondence services and the local "
                    "segmentation aid",
    "DERIVED": "the coherent seed set, the policy charts, the controller contexts, the probes, the gate, the service "
               "states, the scheduler decisions, the world-gaze mappings, the truth-stripped correspondences, the "
               "spherical geometry, the local identity attachment, the H0 fusions and the scene states",
    "REFERENCE / EVALUATION": "the sealed instance catalogs of the new observations (never opened by any NS1c stage)",
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


def head_pose(c: dict) -> tuple[np.ndarray, np.ndarray]:
    return np.asarray(c["head_R_wh"], np.float64), np.asarray(c["head_origin_w_m"], np.float64)


def res(ref: str, run: Path) -> Path:
    import ns1c_core as CORE
    return CORE.resolve(ref, run)


# ------------------------------------------------------------------ source
def accepted_constants() -> dict:
    import fsg6f_public as PUB
    from fov3d.experiments.classroom_oracle import config as public, controller01 as c01
    from fov3d.reconstruction import association
    import tools.classroom_oracle1_epistemic  # noqa: F401
    got = {"SURFACE_FRONTIER": dict(PUB.SURFACE_FRONTIER), "FSG6F_FUSION": dict(PUB.FUSION),
           "FSG6F_OBJECT_ID": int(PUB.OBJECT_ID), "FSG6F_VERGENCE_M": float(PUB.VERGENCE_DISTANCE_M),
           "CYCLOPEAN_GRID_DEG": float(public.CYCLOPEAN_GRID_DEG),
           "MIN_INITIAL_TARGET_POINTS": int(public.MIN_INITIAL_TARGET_POINTS), "FUSION": dict(public.FUSION),
           "SURFACE_ASSOCIATION_RADIUS_M": float(association.SURFACE_ASSOCIATION_RADIUS_M),
           "WATCHDOG": int(c01.WATCHDOG), "MAX_OBJECT_FIXATIONS": int(public.MAX_OBJECT_FIXATIONS)}
    want = {"SURFACE_FRONTIER": SP.SURFACE_FRONTIER, "FSG6F_FUSION": SP.FSG6F_FUSION,
            "FSG6F_OBJECT_ID": SP.FSG6F_OBJECT_ID, "FSG6F_VERGENCE_M": SP.FSG6F_VERGENCE_M,
            "CYCLOPEAN_GRID_DEG": SP.CYCLOPEAN_GRID_DEG, "MIN_INITIAL_TARGET_POINTS": SP.MIN_POINTS,
            "FUSION": {"association_radius_m": SP.ASSOCIATION_RADIUS_M, "hash_cell_m": SP.HASH_CELL_M},
            "SURFACE_ASSOCIATION_RADIUS_M": SP.ASSOCIATION_RADIUS_M, "WATCHDOG": SP.WATCHDOG_EXPECTED,
            "MAX_OBJECT_FIXATIONS": SP.WATCHDOG_EXPECTED}
    if got != want:
        raise SystemExit(f"{PREFIX} STOP the accepted constants differ: {got} != {want}")
    return got


def watchdog_live() -> int:
    from fov3d.experiments.classroom_oracle import controller01 as c01
    return int(c01.WATCHDOG)


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
    if SP.CANONICAL_REMOTE not in origin or not all(anc.values()) or not contract_unchanged:
        raise SystemExit(f"{PREFIX} STOP provenance: origin {origin}; ancestors {anc}; contract unchanged "
                         f"{contract_unchanged}")
    import ns1b_chart as CH
    CH.ensure_policy_modules()
    consts = accepted_constants()
    reads = [ns1a(f) for f in SP.NS1A_PINS] + [ns1b(f) for f in SP.NS1B_PINS]
    g = OpenGuard("ns1c-source", reads, [run / "source"])
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
            sfz = read_json(ns1a("freeze/seed-set-freeze.json"))
            if sfz["files"].get(SP.NS1A_SEED_SET) != SP.NS1A_PINS[SP.NS1A_SEED_SET] or \
                    sfz["files"].get(SP.NS1A_MAPS) != SP.NS1A_PINS[SP.NS1A_MAPS]:
                raise SystemExit(f"{PREFIX} STOP the NS1a seed freeze does not carry the pinned seed set / maps")
            if read_json(ns1a("observations/acquisition-run.json"))["catalog_seal"]["sha256"] != SP.NS1A_CATALOG_SEAL:
                raise SystemExit(f"{PREFIX} STOP the NS1a catalog seal differs")
            man = read_json(ns1b("manifest.json"))
            ns1b_files_ok = all(man["files"].get(rel) == h for rel, h in b_pins.items()
                                if rel not in ("manifest.json", "check-summary.json"))
            summ = read_json(ns1b("check-summary.json"))
            if not ns1b_files_ok or summ["marker"] != "NORTH_STAR1B_CHECKS_PASS" or summ["failed"]:
                raise SystemExit(f"{PREFIX} STOP the NS1b run manifest / check summary does not carry the pinned files")
            out = {"schema": "NS1c-source-v1", "experiment": SP.EXPERIMENT, "code": cs, "origin": origin,
                   "ancestors": anc, "contract": SP.CONTRACT, "contract_commit": SP.CONTRACT_COMMIT,
                   "contract_unchanged": contract_unchanged, "base_commit": SP.BASE_COMMIT,
                   "ns1b_acceptance": SP.NS1B_ACCEPTANCE, "ns1a_acceptance": SP.NS1A_ACCEPTANCE,
                   "source_pins": pins, "accepted_constants": consts, "watchdog": consts["WATCHDOG"],
                   "global_cap": consts["WATCHDOG"], "ns1a_handoff": a_pins, "ns1b_handoff": b_pins,
                   "ns1b_manifest_carries_pins": ns1b_files_ok, "ns1b_check_marker": summ["marker"],
                   "ns1a_catalog_seal": SP.NS1A_CATALOG_SEAL,
                   "adapter": "ns1b_chart.PolicyChartAdapter (accepted NS1b; P1-P3 unchanged)",
                   "scheduler": "fov3d.control.integrated.schedule (accepted; unchanged)"}
            write_json(run / "source/source-manifest.json", out)
    finally:
        write_json(run / "source/source-opened-files.json", guard_record(g))
    return {"pins": len(pins), "ns1a": len(a_pins), "ns1b": len(b_pins), "watchdog": consts["WATCHDOG"]}


# ------------------------------------------------------------------ synthetic known answers
def synthetic(ctx: Ctx) -> dict:
    run = ctx.run
    need(run / "source/source-manifest.json", "source")
    once(run / "synthetic/synthetic-report.json", "the synthetic known answers")
    require_committed(ctx, "synthetic")
    import ns1c_synthetic as SY
    rep = SY.run_all()
    write_json(run / "synthetic/synthetic-report.json", rep)
    if rep["failed"]:
        raise SystemExit(f"{PREFIX} STOP synthetic known answers failed: {rep['failed']}")
    return {"passed": rep["count"] - len(rep["failed"]), "count": rep["count"], "marker": rep["marker"]}


# ------------------------------------------------------------------ section 5: the coherent seed set
def eligibility(ctx: Ctx) -> dict:
    run = ctx.run
    rep = read_json(run / "synthetic/synthetic-report.json") if (run / "synthetic/synthetic-report.json").exists() else {}
    if rep.get("failed") != []:
        raise Refused(f"{PREFIX} REFUSED the synthetic known answers must pass first")
    once(run / "eligibility/coherent-seed-set.json", "the coherent seed set")
    cs = require_committed(ctx, "eligibility")
    import ns1c_core as CORE
    reads = [ns1a(SP.NS1A_SEED_SET), ns1a("freeze/seed-set-freeze.json"), ns1a(SP.NS1A_GAZE_LIST)]
    g = OpenGuard("ns1c-eligibility", reads, [run / "eligibility"])
    try:
        with g:
            for rel in (SP.NS1A_SEED_SET, SP.NS1A_GAZE_LIST, "freeze/seed-set-freeze.json"):
                if sha256(ns1a(rel)) != SP.NS1A_PINS[rel]:
                    raise SystemExit(f"{PREFIX} STOP NS1a {rel} changed")
            el = CORE.derive_coherent_set(read_json(ns1a(SP.NS1A_SEED_SET)))
            import ns1b_core as B
            gazes = B.rank_gazes(read_json(ns1a(SP.NS1A_GAZE_LIST)))
            for row in el["coherent"] + el["deferred"]:
                row["initialization_gaze_deg"] = list(gazes[row["initialized_at_rank"]])
            match = (el["coherent_ids"] == list(SP.EXPECTED_COHERENT)
                     and el["deferred_ids"] == list(SP.EXPECTED_DEFERRED))
            out = {"schema": "NS1c-eligibility-v1", "truth": SP.TRUTH_DERIVED, "code": cs,
                   "statement": "COHERENT_SEED_SET derived from the frozen NS1a seed set by the single-patch rule; "
                                "'coherent' means only single-patch under the NS1a oracle aid; no name, catalog, "
                                "semantic class, NS1b performance or future visibility", **el,
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
    return {"coherent": el["coherent_ids"], "deferred": el["deferred_ids"], "outside": len(el["outside_ids"]),
            "scene": out["scene_ids"]}


def scene_rows(elig: dict) -> list[dict]:
    return elig.get("scene_rows") or elig["coherent"]


# ------------------------------------------------------------------ section 7: charts
def charts(ctx: Ctx) -> dict:
    run = ctx.run
    need(run / "eligibility/coherent-seed-set.json", "eligibility")
    once(run / "charts/policy-charts.json", "the policy charts")
    cs = require_committed(ctx, "charts")
    import ns1b_chart as CH
    import ns1c_core as CORE
    g = OpenGuard("ns1c-charts", [run / "eligibility/coherent-seed-set.json", ns1b("chart/policy-chart.json")],
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
            out = {"schema": "NS1c-charts-v1", "truth": SP.TRUTH_DERIVED, "code": cs, "label": SP.LABEL_CHART,
                   "statement": "one FIXED policy chart per coherent entity (the accepted NS1b construction at its NS1a "
                                "initialization gaze); never recentered; NOT physical head motion",
                   "construction": "x_C = normalize(b - (b.g0) g0), z_C = -g0, y_C = normalize(z_C x x_C); b = +X",
                   "charts": out_rows, "c172_equals_ns1b_chart": same172,
                   "local_domain_deg": {"yaw": [SP.SURFACE_FRONTIER["yaw_min_deg"], SP.SURFACE_FRONTIER["yaw_max_deg"]],
                                        "pitch": [SP.SURFACE_FRONTIER["pitch_min_deg"],
                                                  SP.SURFACE_FRONTIER["pitch_max_deg"]],
                                        "step": SP.SURFACE_FRONTIER["component_step_deg"]},
                   "problems": problems}
            write_json(run / "charts/policy-charts.json", out)
    finally:
        write_json(run / "charts/charts-opened-files.json", guard_record(g))
    if problems:
        raise SystemExit(f"{PREFIX} STOP chart problems (before any execution): {problems}")
    return {"charts": len(out_rows), "c172_equals_ns1b": same172,
            "min_projected_baseline": min(c["projected_baseline_norm"] for c in out_rows.values())}


# ------------------------------------------------------------------ section 9: the initial contexts
def state_file(path: Path, st: dict, valid: np.ndarray) -> None:
    np.savez_compressed(path, ids_left=st["ids_left"], ids_right=st["ids_right"], raw_support_L=st["raw_support_L"],
                        raw_support_R=st["raw_support_R"], matcher_valid=np.asarray(valid, bool))


def arrays_equal(a: dict, b: dict) -> bool:
    return set(a) == set(b) and all(np.asarray(a[k]).dtype == np.asarray(b[k]).dtype
                                    and np.array_equal(np.asarray(a[k]), np.asarray(b[k])) for k in a)


def contexts(ctx: Ctx) -> dict:
    run = ctx.run
    need(run / "charts/policy-charts.json", "charts")
    once(run / "contexts/contexts.json", "the initial controller contexts")
    cs = require_committed(ctx, "contexts")
    import ns1b_chart as CH
    import ns1b_core as B
    import ns1c_core as CORE
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
    g = OpenGuard("ns1c-contexts", reads, [run / "contexts"])
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
                c2 = CORE.context_from_record(rec, run)
                ev2 = CORE.evidence_arrays(c2)
                saved = load_npz(edir / "evidence.npz")
                if not arrays_equal(ev2, saved):
                    raise SystemExit(f"{PREFIX} STOP entity {k}: the context does not reload from its record")
                ents[str(k)] = rec
                diag[str(k)] = {**support, "north_star_map_surfels": rec["map"]["surfels"],
                                "map_local_forward_fraction": float((CH.to_chart(mm["xyz_h"], rr)[:, 2] < -1e-6).mean()),
                                "map_z_H0_positive_fraction": float((mm["xyz_h"][:, 2] > 0).mean()), **info}
            out = {"schema": "NS1c-contexts-v1", "truth": SP.TRUTH_DERIVED, "code": cs,
                   "statement": "one accepted LocalPolicyContext per coherent entity: 172 continues from the accepted "
                                "NS1b post-action context and map (imported exactly); every other entity from its "
                                "frozen NS1a map and saved initialization look through the accepted Classroom matcher "
                                "(CONTROLLER OBSERVATION STATE only); no rerender, no catalog, no name",
                   "inputs_ns1a": inputs, "ranks": ranks,
                   "looks": {SP.ns1a_rank_dir(r): {"matcher": CORE.jsonable(v["meta"]), "fixed_head": v["fixed_head"],
                                                  "matcher_valid": int(v["valid"].sum()),
                                                  "state_sha256": sha256(v["state_path"])} for r, v in looks.items()},
                   "entities": ents, "diagnostics": diag}
            write_json(run / "contexts/contexts.json", out)
    finally:
        write_json(run / "contexts/contexts-opened-files.json", guard_record(g))
    return {"entities": len(ents), "own_looks": {k: v["own_looks"] for k, v in ents.items()},
            "surfels": {k: v["map"]["surfels"] for k, v in ents.items()}}


def import_172(run: Path, edir: Path, lk: dict, ch: dict) -> tuple[dict, dict]:
    """The accepted NS1b post-action context and map of entity 172, imported exactly (arrays equal to the pinned NS1b
    files; the NS1c rank-6 matcher state must equal NS1b's context state bitwise)."""
    import ns1b_core as B
    import ns1c_core as CORE
    for rel in ("context/controller-state.npz", "post/controller-state.npz", "post/evidence.npz",
                "fusion/fused-target-map.npz", "observation/acquisition/calibration.json",
                "freeze/observation-freeze.json", "post/post-action-probe.json"):
        if sha256(ns1b(rel)) != SP.NS1B_PINS[rel]:
            raise SystemExit(f"{PREFIX} STOP the accepted NS1b file {rel} changed")
    mine6 = load_npz(lk["state_path"])
    nb6 = load_npz(ns1b("context/controller-state.npz"))
    if not arrays_equal(mine6, nb6):
        raise SystemExit(f"{PREFIX} STOP the NS1c rank-6 controller state differs from NS1b's (one look, one state)")
    post = load_npz(ns1b("post/controller-state.npz"))
    p = run / "contexts/looks/ns1b-action/controller-state.npz"
    p.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(p, **post)
    ev = load_npz(ns1b("post/evidence.npz"))
    np.savez_compressed(edir / "evidence.npz", **ev)
    fm = load_npz(ns1b("fusion/fused-target-map.npz"))
    np.savez_compressed(edir / "map-H0.npz", **fm)
    copies = {"ns1b-action state": arrays_equal(load_npz(p), post), "evidence": arrays_equal(load_npz(edir / "evidence.npz"),
                                                                                             ev),
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
                                  "action_state": "post/controller-state.npz", "arrays_equal": copies,
                                  "rank6_state_equals_ns1c": True}}
    # an independent recomputation: the evidence rebuilt from the two looks under C_172 equals the imported evidence
    r = np.asarray(ch["R_HC"], np.float64)
    rec_tmp = {**rec, "temporary_entity_id": SP.CONTINUING}
    rebuilt = CORE.evidence_arrays(CORE.rebuild_context(rec_tmp, run, r))
    if not arrays_equal(rebuilt, ev):
        raise SystemExit(f"{PREFIX} STOP the NS1b evidence of 172 is not reproduced from its two looks")
    if sha256(ns1b("fusion/fusion.json")) != SP.NS1B_PINS["fusion/fusion.json"]:
        raise SystemExit(f"{PREFIX} STOP the accepted NS1b fusion record changed")
    info = {"ns1b_action_support": {"controller_state_target_support": int(pp["matcher_target_valid_points"]),
                                    "controller_state_target_pixels_L": int((post["ids_left"] == SP.CONTINUING).sum()),
                                    "north_star_target_points": int(read_json(ns1b("fusion/fusion.json"))[
                                        "measured_points"])},
            "evidence_cells": {n: int(v.sum()) for n, v in ev.items()}, "evidence_rebuilt_equal": True}
    del B
    return rec, info


# ------------------------------------------------------------------ section 11: the initial probe
def probe_reads(run: Path, recs: dict) -> list[Path]:
    out = []
    for rec in recs.values():
        for look in rec["looks"]:
            out += [res(look["calibration"], run), res(look["state"], run)]
        out += [res(rec["evidence"]["path"], run), res(rec["map"]["path"], run)]
    return sorted(set(out))


def initial_probe(ctx: Ctx) -> dict:
    run = ctx.run
    need(run / "contexts/contexts.json", "contexts")
    once(run / "initial-probe/initial-service-table.json", "the initial probe of every coherent entity")
    cs = require_committed(ctx, "initial-probe")
    import ns1b_chart as CH
    import ns1c_core as CORE
    import ns1a_core  # noqa: F401
    CH.ensure_policy_modules()
    import fsg6f_frontier  # noqa: F401
    recs = read_json(run / "contexts/contexts.json")["entities"]
    wd = watchdog_live()
    reads = probe_reads(run, recs) + [run / "contexts/contexts.json", run / "charts/policy-charts.json",
                                      run / "eligibility/coherent-seed-set.json", ns1b("post/post-action-probe.json")]
    (run / "initial-probe/probes").mkdir(parents=True, exist_ok=True)
    (run / "scene").mkdir(parents=True, exist_ok=True)
    g = OpenGuard("ns1c-initial-probe", reads, [run / "initial-probe", run / "scene"])
    problems, table = [], []
    try:
        with g:
            el = read_json(run / "eligibility/coherent-seed-set.json")
            chs = read_json(run / "charts/policy-charts.json")["charts"]
            nbp = read_json(ns1b("post/post-action-probe.json"))
            ents = {}
            repro = None
            for k in sorted(recs, key=int):
                rec = dict(recs[k])
                ch = chs[k]
                cal0 = json.loads(res(rec["looks"][0]["calibration"], run).read_text())
                hr, ho = head_pose(cal0)
                try:
                    out = CORE.probe_entity(rec, run, ch, hr, ho, f"initial probe entity {k}")
                except Exception as exc:  # noqa: BLE001  (a refusal of the accepted code is Outcome 4, recorded)
                    problems.append(f"entity {k}: the accepted probe raised {type(exc).__name__}: {exc}")
                    continue
                rot = CORE.rotation_invariance(rec, run, ch, out, hr, ho)
                if not all(r_["pass"] for r_ in rot):
                    problems.append(f"entity {k}: baseline-rotation invariance failed")
                if out["proposal"] is not None and out["proposal"]["roundtrip_error_deg"] > SP.GAZE_ROUNDTRIP_TOL_DEG:
                    problems.append(f"entity {k}: the chart / world gaze round trip fails")
                if int(k) == SP.CONTINUING:
                    diffs = CORE.reproduce_ns1b_post(out, nbp["probe"])
                    exp = CORE.expected_ns1b_post(out)
                    repro = {"differences": diffs[:20], "difference_count": len(diffs), "expected": exp,
                             "accepted_record": "ns1b:post/post-action-probe.json",
                             "accepted_sha256": SP.NS1B_PINS["post/post-action-probe.json"],
                             "reproduced": not diffs and exp["equal"]}
                    if not repro["reproduced"]:
                        problems.append(f"HARD STOP: the NS1b post-action probe of 172 is not reproduced: {diffs[:5]}")
                full = {"schema": "NS1c-probe-v1", "truth": SP.TRUTH_DERIVED, "entity": int(k),
                        "computed_at": "initial-probe", "revision": rec["revision"], "probe": CORE.jsonable(out),
                        "baseline_rotation_invariance": rot}
                pth = run / f"initial-probe/probes/e{int(k):05d}.json"
                write_json(pth, full)
                srv = CORE.service(out, rec["own_looks"], wd, None)
                rec.update({"probe": {"path": f"run:initial-probe/probes/e{int(k):05d}.json", "sha256": sha256(pth),
                                      "revision": rec["revision"], "provenance": "fresh",
                                      "computed_at": "initial-probe"},
                            "service": srv, "gated_state": CORE.gated_state(out),
                            "proposal": CORE.proposal_summary(out), "gate": CORE.gate_summary(out),
                            "fsg6f": CORE.fsg6f_summary(out), "quiet_since_step": None})
                ents[k] = rec
                p = out["proposal"]
                table.append({"temporary_entity_id": int(k), "initialization_rank": rec["initialization_rank"],
                              "map_surfels": rec["map"]["surfels"], "own_looks": rec["own_looks"],
                              "current_local_gaze": rec["current_local_gaze"],
                              "fsg6f": out["summary"]["fsg6f"]["reason"],
                              "cyclopean": (out["summary"].get("cyclopean") or {}).get("reason"),
                              "proposal_source": None if p is None else p["source"],
                              "proposed_local_gaze": None if p is None else p["local_gaze_deg"],
                              "proposed_H0_gaze": None if p is None else p["world_gaze_deg"],
                              "gate_admissible": bool(out["gate"]["admissible"]), "gate_reason": out["gate"]["reason"],
                              "novel_serviceable_support": ((out["gate"].get("detail") or {}).get("counts") or {}).get(
                                  "novel_service_count"),
                              "service_state": srv["label"], "rotation_invariance": [r_["pass"] for r_ in rot]})
            tab = {"schema": "NS1c-initial-service-table-v1", "truth": SP.TRUTH_DERIVED, "code": cs,
                   "statement": "every coherent entity probed exactly once before any render: the accepted FSG6f -> "
                                "Cyclopean probe and the v1 gate under the entity's fixed policy chart; admissible "
                                "proposal -> ACTIONABLE, otherwise QUIET; nothing executed",
                   "watchdog": wd, "rows": table, "ns1b_reproduction": repro, "problems": problems,
                   "deferred": [{"temporary_entity_id": r_["temporary_entity_id"], "state": SP.DEFERRED_STATE,
                                 "contributing_patches": r_["contributing_patches"]} for r_ in el["deferred"]],
                   "policy_configuration_used": CORE.jsonable(policy_configuration())}
            write_json(run / "initial-probe/initial-service-table.json", tab)
            if not problems:
                scene = {"schema": "NS1c-scene-state-v1", "truth": SP.TRUTH_DERIVED, "label": "initial",
                         "global_step": -1, "code": cs, "current": SP.CONTINUING, "previous": None,
                         "attention_bout": 1, "executed_actions": 0, "watchdog": wd, "cap": wd,
                         "scene_ids": sorted(int(k) for k in ents), "coherent_ids": el["coherent_ids"],
                         "deferred": [{"temporary_entity_id": r_["temporary_entity_id"], "state": SP.DEFERRED_STATE,
                                       "contributing_patches": r_["contributing_patches"], "in_scheduler": False}
                                      for r_ in el["deferred"]],
                         "entities": ents, "reactivated_since_attended": [], "events": [],
                         "probe_calls": len(ents), "probe_cache_hits": 0, "stopped": False, "stop": None,
                         "last_decision": None, "last_action": None,
                         "table": [CORE.entity_row(ents[k]) for k in sorted(ents, key=int)]}
                write_json(run / SP.scene_state_rel("initial"), scene)
    finally:
        write_json(run / "initial-probe/initial-probe-opened-files.json", guard_record(g))
    if problems:
        raise SystemExit(f"{PREFIX} STOP initial probe (no render): {problems}")
    return {"rows": [[r_["temporary_entity_id"], r_["service_state"], r_["proposed_local_gaze"]] for r_ in table],
            "ns1b_reproduced": repro["reproduced"] if repro else None}


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
            "FUSION": dict(public.FUSION), "gate": "controller02.final_look_gate_v1 (accepted)"}


# ------------------------------------------------------------------ the scene state of a step
def prev_scene_rel(step: int) -> str:
    return SP.scene_state_rel("initial" if step == 0 else f"after-step-{step - 1:02d}")


def latest_scene(run: Path) -> tuple[str, dict]:
    sts = sorted((run / "scene").glob("state-after-step-*.json"))
    rel = str(sts[-1].relative_to(run)) if sts else SP.scene_state_rel("initial")
    return rel, read_json(run / rel)


# ------------------------------------------------------------------ section 14.1: schedule
def schedule(ctx: Ctx) -> dict:
    run, k = ctx.run, int(ctx.step)
    sd = ctx.sd()
    need(run / prev_scene_rel(k), f"the scene state before step {k}")
    if (run / SP.scene_state_rel(f"after-step-{k:02d}")).exists() or (run / SP.step_dir(k + 1)).exists():
        raise Refused(f"{PREFIX} REFUSED step {k} is not the next step")
    once(sd / "plan/decision.json", f"the decision of step {k}")
    if (run / "scene/terminal.json").exists():
        raise Refused(f"{PREFIX} REFUSED the scheduler already reached a terminal decision")
    cs = require_committed(ctx, "schedule")
    import ns1b_chart as CH
    import ns1c_core as CORE
    CH.ensure_policy_modules()
    import ns1a_core  # noqa: F401
    from fov3d.control import integrated  # noqa: F401
    prev = read_json(run / prev_scene_rel(k))
    try:
        CORE.require_not_stopped(prev)
    except CORE.ProcessRefused as exc:
        raise Refused(f"{PREFIX} REFUSED {exc}")
    rec_t = None
    reads = [run / prev_scene_rel(k), run / "charts/policy-charts.json"]
    for rec in prev["entities"].values():
        reads += [res(rec["probe"]["path"], run), res(rec["looks"][0]["calibration"], run)]
    (sd / "plan").mkdir(parents=True, exist_ok=True)
    g = OpenGuard(f"ns1c-schedule-{k:02d}", reads, [sd / "plan", run / "scene"])
    terminal = cap = None
    try:
        with g:
            rows = CORE.summaries(prev["entities"], prev["scene_ids"])
            dec = CORE.schedule(prev["current"], rows)
            reason = dec["reason"]
            if dec["kind"] == "attend" and reason == "switch" and dec["target_id"] in prev["reactivated_since_attended"]:
                reason = "natural_reactivation"
            bout = int(prev["attention_bout"]) + (1 if dec["reason"] in ("initial", "switch") else 0)
            out = {"schema": "NS1c-decision-v1", "truth": SP.TRUTH_DERIVED, "code": cs, "global_step": k,
                   "statement": "the accepted fov3d.control.integrated.schedule on the coherent entities' service "
                                "summaries (current object, identity and service state only)",
                   "scheduler": SP.LABEL_SCHEDULER, "kind": dec["kind"], "scheduler_decision": dec,
                   "scheduler_reason": reason, "current_before": prev["current"], "attention_bout": bout,
                   "executed_before": prev["executed_actions"], "cap": prev["cap"],
                   "scene_state_before": {"path": prev_scene_rel(k), "sha256": sha256(run / prev_scene_rel(k))}}
            if dec["kind"] == "terminal":
                terminal = dec["terminal"]
                CORE.terminal_label(terminal["type"])
                out["terminal"] = terminal
                write_json(sd / "plan/decision.json", out)
                write_json(run / "scene/terminal.json", {**out, "outcome_reading": (
                    "Outcome 3 - no serviceable second entity: " + terminal["label"])})
            else:
                try:
                    CORE.require_under_cap(prev["executed_actions"], prev["cap"])
                except CORE.ProcessRefused as exc:
                    cap = str(exc)
                    out["kind"] = "cap"
                    out["cap_reached"] = {"type": "CapReached", "cap": prev["cap"], "reason": cap}
                    write_json(sd / "plan/decision.json", out)
                    write_json(run / "scene/terminal.json", {**out, "outcome_reading": "Outcome 4 - global cap reached"})
                if cap is None:
                    t = int(dec["target_id"])
                    rec_t = prev["entities"][str(t)]
                    if rec_t["service"]["state"] != SP.SERVICE_ACTIONABLE or not rec_t["gate"]["admissible"]:
                        raise SystemExit(f"{PREFIX} STOP the scheduler attended {t}, which has no admissible proposal")
                    pf = res(rec_t["probe"]["path"], run)
                    if sha256(pf) != rec_t["probe"]["sha256"]:
                        raise SystemExit(f"{PREFIX} STOP the probe record of {t} changed")
                    prop = read_json(pf)["probe"]["proposal"]
                    chart = read_json(run / "charts/policy-charts.json")["charts"][str(t)]
                    cal0 = json.loads(res(rec_t["looks"][0]["calibration"], run).read_text())
                    hr, ho = head_pose(cal0)
                    plan = CORE.plan_action(prop, chart, hr, ho)
                    if (plan["roundtrip_error_deg"] > SP.GAZE_ROUNDTRIP_TOL_DEG
                            or plan["world_gaze_deg"] != prop["world_gaze_deg"]
                            or not plan["physical_calibration_test"]["ok"]):
                        raise SystemExit(f"{PREFIX} STOP the world gaze / planned calibration of step {k} fails "
                                         "(Outcome 4)")
                    b = plan.pop("planned_calibration_bytes")
                    planned = plan.pop("planned_calibration")
                    (sd / "plan/planned-calibration.json").write_bytes(b)
                    out["action"] = {"global_step": k, "target": t, "source": prop["source"],
                                     "local_gaze_deg": plan["local_gaze_deg"], "world_gaze_deg": plan["world_gaze_deg"],
                                     "planned_calibration_sha256": hashlib.sha256(b).hexdigest(),
                                     "patch_id": SP.patch_id(k), "own_looks_before": rec_t["own_looks"],
                                     "chart_id": rec_t["chart_id"], "chart_sha256": rec_t["chart_sha256"],
                                     "proposal_probe": rec_t["probe"]}
                    out["plan"] = {**plan, "planned_gaze_H0_deg": list(planned["gaze_yaw_pitch_deg"])}
                    out["previous_target"] = prev["current"]
                    out["target_transition"] = "retain" if prev["current"] == t else f"{prev['current']}->{t}"
                    write_json(sd / "plan/decision.json", out)
    finally:
        write_json(sd / "plan/plan-opened-files.json", guard_record(g))
    if cap is not None:
        raise SystemExit(f"{PREFIX} STOP {cap} (Outcome 4)")
    if terminal is not None:
        return {"kind": "terminal", "terminal": terminal}
    return {"kind": "attend", "target": out["action"]["target"], "reason": reason,
            "local": out["action"]["local_gaze_deg"], "world": out["action"]["world_gaze_deg"]}


def require_action(ctx: Ctx, what: str) -> dict:
    sd = ctx.sd()
    need(sd / "plan/decision.json", f"schedule (step {ctx.step})")
    d = read_json(sd / "plan/decision.json")
    if d.get("kind") != "attend" or not d.get("action"):
        raise Refused(f"{PREFIX} REFUSED {what} is not applicable: step {ctx.step} has no scheduled action "
                      f"({d.get('kind')})")
    return {**d, "action": d["action"]}


# ------------------------------------------------------------------ Blender (preflight / acquire of a step)
def blender(ctx: Ctx, args: list[str], log: Path, factory: bool = False) -> None:
    log.parent.mkdir(parents=True, exist_ok=True)
    cmd = [SP.BLENDER, "-b"] + (["--factory-startup"] if factory else [str(REPO / SP.BLEND)])
    cmd += ["--python-exit-code", "1", "-P", str(HERE / "ns1c_render.py"), "--"] + args
    with open(log, "w") as f:
        p = subprocess.run(cmd, cwd=REPO, stdout=f, stderr=subprocess.STDOUT)
    text = log.read_text(errors="replace")
    if p.returncode != 0 or "[ns1c-render] COMPLETE" not in text or "[ns1c-render] FAILED" in text:
        raise SystemExit(f"{PREFIX} STOP Blender failed (exit {p.returncode}); see {log}")


def preflight(ctx: Ctx) -> dict:
    sd = ctx.sd()
    require_action(ctx, "preflight")
    once(sd / "preflight/preflight.json", f"the preflight of step {ctx.step}")
    require_committed(ctx, "preflight")
    if sha256(REPO / SP.BLEND) != SP.BLEND_SHA256:
        raise SystemExit(f"{PREFIX} STOP the Classroom blend changed")
    blender(ctx, ["--mode", "preflight", "--step-dir", str(sd)], sd / "preflight/blender.log")
    return {k: v for k, v in read_json(sd / "preflight/preflight.json").items() if k in ("rendered", "gaze_H0_deg")}


def acquire(ctx: Ctx) -> dict:
    sd = ctx.sd()
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


# ------------------------------------------------------------------ freeze-observation
def observation_files() -> list[str]:
    return [SP.ACQ_RUN_REL] + [f"{SP.OBS_ACQ}/{n}" for n in SP.OBS_ACQ_FILES] + [f"{SP.OBS_AID}/{n}"
                                                                                 for n in SP.OBS_AID_FILES]


def freeze_observation(ctx: Ctx) -> dict:
    sd = ctx.sd()
    d = require_action(ctx, "freeze-observation")
    need(sd / SP.ACQ_RUN_REL, "acquire")
    once(sd / "freeze/observation-freeze.json", f"the observation freeze of step {ctx.step}")
    cs = require_committed(ctx, "freeze-observation")
    files = observation_files()
    g = OpenGuard(f"ns1c-freeze-observation-{ctx.step:02d}", [sd / f for f in files] + [
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
            fz = {"schema": "NS1c-observation-freeze-v1", "truth": SP.TRUTH_ORACLE, "frozen_utc": utc(), "code": cs,
                  "global_step": ctx.step, "target": d["action"]["target"],
                  "statement": "the step's one binocular observation at the mapped H0 gaze; never re-rendered. The "
                               "sealed catalog is NOT opened: its Blender-recorded seal is carried", "spp": ar["spp"],
                  "catalog_seal": ar["catalog_seal"], "files": hashes}
            write_json(sd / "freeze/observation-freeze.json", fz)
    finally:
        write_json(sd / "freeze/observation-freeze-opened-files.json", guard_record(g))
    return {"files": len(hashes), "spp": ar["spp"]}


# ------------------------------------------------------------------ section 14: PERFECT correspondence -> geometry -> id
CORR_FILES = ("correspondence/oracle-correspondences.npz", "correspondence/oracle-summary.json",
              "correspondence/core-class-map.npz", "correspondence/correspondence-opened-files.json")
GEOM_FILES = ("geometry/left-core-rays.npz", "geometry/epipolar-result.npz", "geometry/geometry-summary.json",
              "geometry/geometry-opened-files.json")
SEG_FILES = ("segmentation/local-identity.npz", "segmentation/identity-summary.json")


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
    g = OpenGuard(f"ns1c-oracle-{ctx.step:02d}", [cal, ref, sd / "freeze/observation-freeze.json"], [odir])
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
            summary = {"schema": "NS1c-oracle-summary-v1", "truth": SP.TRUTH_DERIVED, "label": SP.LABEL_ORACLE_CORR,
                       "statement": "PERFECT / ORACLE CORRESPONDENCE (accepted AB1b compute_oracle, read-only): "
                                    "Position and Object Index were used here, and only here, to choose and project the "
                                    "matches; the product holds core row / col and continuous uv_L / uv_R only",
                       "oracle": O.SP.ORACLE, "oracle_config_sha256": O.SP.config_sha256(O.SP.ORACLE),
                       "inputs": inputs, "product_keys": sorted(product),
                       "core_class_counts": {str(k): int((cls == k).sum()) for k in range(4)}, **summ}
            write_json(odir / "oracle-summary.json", summary)
    finally:
        write_json(odir / "correspondence-opened-files.json", guard_record(g))
    return {"correspondences": summary["correspondences"]}


def freeze_correspondence(ctx: Ctx) -> dict:
    sd = ctx.sd()
    require_action(ctx, "freeze-correspondence")
    need(sd / "correspondence/oracle-correspondences.npz", "perfect-correspondence")
    once(sd / "freeze/correspondence-freeze.json", f"the correspondence freeze of step {ctx.step}")
    cs = require_committed(ctx, "freeze-correspondence")
    import ab1b_geometry as BG
    g = OpenGuard(f"ns1c-freeze-correspondence-{ctx.step:02d}", [sd / f for f in CORR_FILES], [sd / "freeze"])
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
            fz = {"schema": "NS1c-correspondence-freeze-v1", "truth": SP.TRUTH_DERIVED, "frozen_utc": utc(), "code": cs,
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
    g = OpenGuard(f"ns1c-geometry-{ctx.step:02d}", [cal, prod_p], [odir])
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
            summary = {"schema": "NS1c-geometry-summary-v1", "truth": SP.TRUTH_DERIVED, "label": SP.LABEL_GEOMETRY,
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
    require_action(ctx, "freeze-geometry")
    need(sd / "geometry/epipolar-result.npz", "spherical-geometry")
    once(sd / "freeze/geometry-freeze.json", f"the geometry freeze of step {ctx.step}")
    cs = require_committed(ctx, "freeze-geometry")
    cfz = sd / "freeze/correspondence-freeze.json"
    g = OpenGuard(f"ns1c-freeze-geometry-{ctx.step:02d}", [sd / f for f in GEOM_FILES + CORR_FILES] + [cfz],
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
            fz = {"schema": "NS1c-geometry-freeze-v1", "truth": SP.TRUTH_DERIVED, "frozen_utc": utc(), "code": cs,
                  "global_step": ctx.step,
                  "statement": "the truth-free spherical geometry, frozen before any identity is attached",
                  "correspondence_freeze_sha256": sha256(cfz), "files": {f: sha256(sd / f) for f in GEOM_FILES}}
            write_json(sd / "freeze/geometry-freeze.json", fz)
    finally:
        write_json(sd / "freeze/geometry-freeze-opened-files.json", guard_record(g))
    return {"files": len(GEOM_FILES)}


def local_oracle_segmentation(ctx: Ctx) -> dict:
    sd = ctx.sd()
    require_action(ctx, "local-oracle-segmentation")
    need(sd / "freeze/geometry-freeze.json", "freeze-geometry")
    once(sd / "segmentation", f"the local oracle segmentation of step {ctx.step}")
    require_committed(ctx, "local-oracle-segmentation")
    import ns1a_core as NCORE
    odir = sd / "segmentation"
    odir.mkdir(parents=True, exist_ok=True)
    reads = [sd / "freeze/geometry-freeze.json"] + [sd / f for f in GEOM_FILES] + [
        sd / "correspondence/oracle-correspondences.npz", sd / f"{SP.OBS_AID}/reference-observation.npz"]
    g = OpenGuard(f"ns1c-segmentation-{ctx.step:02d}", reads, [odir])
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
            summ = {"schema": "NS1c-identity-summary-v1", "truth": SP.TRUTH_DERIVED, "label": SP.LABEL_SEGMENTATION,
                    "statement": "ORACLE SEGMENTATION AID: temporary_entity_id = the left raw-core Object Index at the "
                                 "exact uv_L centre of each valid correspondence; not natural identity; no catalog, no "
                                 "names", "reference_members_read": list(SP.SEGMENTATION_MEMBERS),
                    **NCORE.identity_summary(ids)}
            write_json(odir / "identity-summary.json", summ)
    finally:
        write_json(odir / "segmentation-opened-files.json", guard_record(g, {"reference_members_read":
                                                                              list(SP.SEGMENTATION_MEMBERS)}))
    return {"entities": len(summ["entities"])}


# ------------------------------------------------------------------ section 16: target-only H0 fusion
def fuse(ctx: Ctx) -> dict:
    run, sd, k = ctx.run, ctx.sd(), int(ctx.step)
    d = require_action(ctx, "fuse")
    need(sd / "segmentation/identity-summary.json", "local-oracle-segmentation")
    once(sd / "fusion/fusion.json", f"the H0 fusion of step {k}")
    cs = require_committed(ctx, "fuse")
    import ns1b_core as B
    import ns1c_core as CORE
    from fov3d.reconstruction import surface_map as SMOD  # noqa: F401
    target = int(d["action"]["target"])
    prev = read_json(run / prev_scene_rel(k))
    mrec = prev["entities"][str(target)]["map"]
    reads = [sd / "freeze/geometry-freeze.json"] + [sd / f for f in GEOM_FILES + SEG_FILES] + [
        sd / "correspondence/oracle-correspondences.npz", sd / f"{SP.OBS_ACQ}/rgb-observation.npz",
        sd / "plan/decision.json", sd / "segmentation/segmentation-opened-files.json", run / prev_scene_rel(k),
        res(mrec["path"], run)]
    (sd / "fusion").mkdir(parents=True, exist_ok=True)
    g = OpenGuard(f"ns1c-fuse-{k:02d}", reads, [sd / "fusion"])
    try:
        with g:
            verify_record_hashes(sd, "freeze/geometry-freeze.json")
            if sha256(res(mrec["path"], run)) != mrec["sha256"]:
                raise SystemExit(f"{PREFIX} STOP the target map changed since the scene state")
            prod = load_npz(sd / "correspondence/oracle-correspondences.npz")
            r_ = read_members(sd / "geometry/epipolar-result.npz", ("P_epi", "valid_epi"))
            idn = load_npz(sd / "segmentation/local-identity.npz")
            rgb_l = read_members(sd / f"{SP.OBS_ACQ}/rgb-observation.npz", ("rgb_L",))["rgb_L"]
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
            idsum = read_json(sd / "segmentation/identity-summary.json")
            incidental = sorted(int(e) for e in idsum["entities"] if int(e) != target)
            out = {"schema": "NS1c-fusion-v1", "truth": SP.TRUTH_DERIVED, "code": cs, "global_step": k,
                   "statement": "the selected target's points of the frozen spherical measurement, fused into ONLY that "
                                "target's H0 map with the accepted surface map (12 mm / 12 mm) in canonical H0, with one "
                                "exact replay; incidental ids in view are never fused",
                   "target": target, "patch_id": patch["patch_id"], "map_before_path": mrec["path"],
                   "map_before_sha256": mrec["sha256"], "valid_correspondences":
                       int(np.asarray(r_["valid_epi"], bool).sum()), "entities_in_view": idsum["entities"],
                   "incidental_ids_not_fused": incidental, "local_gaze_deg": d["action"]["local_gaze_deg"],
                   "world_gaze_deg": d["action"]["world_gaze_deg"], **rec}
            write_json(sd / "fusion/fusion.json", out)
    finally:
        write_json(sd / "fusion/fusion-opened-files.json", guard_record(g))
    return {kk: out[kk] for kk in ("action", "target", "map_before", "measured_points", "matched", "new", "map_after")}


# ------------------------------------------------------------------ section 14.11: update, re-probe, scene state
def update(ctx: Ctx) -> dict:
    run, sd, k = ctx.run, ctx.sd(), int(ctx.step)
    d = require_action(ctx, "update")
    need(sd / "fusion/fusion.json", "fuse")
    once(sd / "update/update.json", f"the update of step {k}")
    cs = require_committed(ctx, "update")
    import ns1b_chart as CH
    import ns1b_core as B
    import ns1c_core as CORE
    CH.ensure_policy_modules()
    import ns1a_core  # noqa: F401
    import fsg6f_frontier  # noqa: F401
    prev = read_json(run / prev_scene_rel(k))
    t = int(d["action"]["target"])
    rec_t = prev["entities"][str(t)]
    reads = probe_reads(run, {str(t): rec_t}) + [
        run / prev_scene_rel(k), run / "charts/policy-charts.json", sd / "plan/decision.json",
        sd / "fusion/fusion.json", sd / "fusion/fused-target-map.npz", sd / "freeze/observation-freeze.json",
        sd / f"{SP.OBS_ACQ}/calibration.json", sd / f"{SP.OBS_ACQ}/rgb-observation.npz",
        sd / f"{SP.OBS_AID}/reference-observation.npz"]
    (sd / "update/probes").mkdir(parents=True, exist_ok=True)
    g = OpenGuard(f"ns1c-update-{k:02d}", reads, [sd / "update", run / "scene", run / "freeze"])
    try:
        with g:
            fz = read_json(sd / "freeze/observation-freeze.json")
            for rel in (f"{SP.OBS_ACQ}/calibration.json", f"{SP.OBS_ACQ}/rgb-observation.npz",
                        f"{SP.OBS_AID}/reference-observation.npz"):
                if sha256(sd / rel) != fz["files"][rel]:
                    raise SystemExit(f"{PREFIX} STOP {rel} changed after the observation freeze")
            chs = read_json(run / "charts/policy-charts.json")["charts"]
            ch = chs[str(t)]
            r = np.asarray(ch["R_HC"], np.float64)
            fu = read_json(sd / "fusion/fusion.json")
            wd = int(prev["watchdog"])
            # -- the target's controller observation state and context (Controller-01 observe order)
            cal1 = read_json(sd / f"{SP.OBS_ACQ}/calibration.json")
            rec1, meta1, st1 = B.matcher_state(cal1, load_npz(sd / f"{SP.OBS_ACQ}/rgb-observation.npz"),
                                               load_npz(sd / f"{SP.OBS_AID}/reference-observation.npz"))
            state_file(sd / "update/controller-state.npz", st1, rec1["valid"])
            c_ctx = CORE.context_from_record(rec_t, run)
            ad = B.add_look(c_ctx, cal1, st1, rec1["valid"], r, tuple(d["action"]["local_gaze_deg"]))
            ev = B.evidence_arrays(c_ctx)
            np.savez_compressed(sd / "update/evidence.npz", **ev)
            new = json.loads(json.dumps(rec_t))
            new["looks"].append({"source": f"NS1c step {k:02d} ({SP.patch_id(k)})",
                                 "calibration": f"run:{SP.step_dir(k)}/{SP.OBS_ACQ}/calibration.json",
                                 "calibration_sha256": sha256(sd / f"{SP.OBS_ACQ}/calibration.json"),
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
            # -- the target's probe (its revision changed); every other entity through the cache
            m_now = load_npz(res(new["map"]["path"], run))
            hr, ho = head_pose(json.loads(res(rec_t["looks"][0]["calibration"], run).read_text()))
            out = B.probe(c_ctx, CH.to_chart(np.asarray(m_now["xyz_h"], np.float64), r), r, CH.north_star_sensor,
                          hr, ho, SP.PROFILE, np.asarray(ch["g0_H0"], np.float64),
                          f"post-action probe of entity {t} (step {k})")
            pth = sd / f"update/probes/e{t:05d}.json"
            write_json(pth, {"schema": "NS1c-probe-v1", "truth": SP.TRUTH_DERIVED, "entity": t,
                             "computed_at": f"step-{k:02d}", "revision": new["revision"], "probe": CORE.jsonable(out),
                             "executed": False})
            ents, calls, hits = {}, 0, 0
            for key, rec in sorted(prev["entities"].items(), key=lambda kv: int(kv[0])):
                if int(key) == t:
                    if CORE.revision(new) == rec["probe"]["revision"]:
                        raise SystemExit(f"{PREFIX} STOP the target's revision did not change")
                    calls += 1
                    blocked = rec["service"]["blocked_reason"] if rec["service"]["state"] == SP.SERVICE_BLOCKED else None
                    srv = CORE.service(out, new["own_looks"], wd, blocked)
                    new.update({"probe": {"path": f"run:{SP.step_dir(k)}/update/probes/e{t:05d}.json",
                                          "sha256": sha256(pth), "revision": new["revision"], "provenance": "fresh",
                                          "computed_at": f"step-{k:02d}"},
                                "service": srv, "gated_state": CORE.gated_state(out),
                                "proposal": CORE.proposal_summary(out), "gate": CORE.gate_summary(out),
                                "fsg6f": CORE.fsg6f_summary(out)})
                    ents[key] = new
                else:
                    if CORE.revision(rec) != rec["probe"]["revision"]:
                        raise SystemExit(f"{PREFIX} STOP an untouched entity's revision changed: {key}")
                    hits += 1          # unchanged revision: the accepted cache reuses the probe (and its service)
                    same = json.loads(json.dumps(rec))
                    same["probe"] = {**rec["probe"], "provenance": "cached"}
                    ents[key] = same
            events = CORE.refresh_events(prev["entities"], ents, k, t)
            for e in events:
                if e["event"] == "quiet":
                    ents[str(e["object"])]["quiet_since_step"] = k
            reac = set(prev["reactivated_since_attended"]) - {t}
            reac |= {e["object"] for e in events if e["event"] == "natural_reactivation"}
            untouched_changes = [e for e in events if e["object"] != t]
            stop = CORE.stop_event(t, fu["action"])
            scene = {"schema": "NS1c-scene-state-v1", "truth": SP.TRUTH_DERIVED, "label": f"after-step-{k:02d}",
                     "global_step": k, "code": cs, "current": t, "previous": prev["current"],
                     "attention_bout": int(d["attention_bout"]), "executed_actions": int(prev["executed_actions"]) + 1,
                     "watchdog": wd, "cap": prev["cap"], "scene_ids": prev["scene_ids"],
                     "coherent_ids": prev["coherent_ids"], "deferred": prev["deferred"], "entities": ents,
                     "reactivated_since_attended": sorted(reac), "events": events,
                     "untouched_state_changes": untouched_changes,
                     "probe_calls": int(prev["probe_calls"]) + calls, "probe_cache_hits": int(prev["probe_cache_hits"]) + hits,
                     "stopped": bool(stop), "stop": None,
                     "last_decision": {"global_step": k, "kind": d["kind"], "scheduler_decision": d["scheduler_decision"],
                                       "scheduler_reason": d["scheduler_reason"], "attention_bout": d["attention_bout"],
                                       "previous_target": d.get("previous_target"),
                                       "target_transition": d.get("target_transition")},
                     "last_action": {"global_step": k, "target": t, "local_gaze_deg": d["action"]["local_gaze_deg"],
                                     "world_gaze_deg": d["action"]["world_gaze_deg"], "fusion": fu["action"],
                                     "patch_id": fu["patch_id"]},
                     "table": [CORE.entity_row(ents[kk]) for kk in sorted(ents, key=int)]}
            if stop:
                scene["stop"] = {"global_step": k, "event": "FIRST SUCCESSFUL ACTION ON A TARGET OTHER THAN 172",
                                 "from": prev["current"], "to": t, "scheduler_reason": d["scheduler_reason"],
                                 "fusion": fu["action"],
                                 "post_action_probe_of_new_target": {"path": new["probe"]["path"],
                                                                     "state": new["service"]["label"],
                                                                     "proposal": new["proposal"], "executed": False},
                                 "statement": "the canonical stop: one read-only post-action probe of the new target; "
                                              "the scene table recomputed once; the scene state frozen; no further "
                                              "action is scheduled"}
            rel = SP.scene_state_rel(f"after-step-{k:02d}")
            write_json(run / rel, scene)
            upd = {"schema": "NS1c-update-v1", "truth": SP.TRUTH_DERIVED, "code": cs, "global_step": k, "target": t,
                   "statement": "the target's controller observation state and context updated in Controller-01 observe "
                                "order (evidence through P2 under its fixed chart); the target re-probed (revision "
                                "changed); every other coherent entity reused from the cache (revision unchanged)",
                   "matcher": CORE.jsonable(meta1),
                   "controller_state_target_support": int((np.asarray(rec1["valid"], bool)
                                                           & (np.asarray(rec1["instance_id"]) == t)).sum()),
                   "controller_state_target_pixels_L": int((st1["ids_left"] == t).sum()),
                   "north_star_target_points": int(fu["measured_points"]), "evidence_adapter": ad,
                   "evidence_cells": {n: int(v.sum()) for n, v in ev.items()}, "own_looks": new["own_looks"],
                   "visited": new["visited"], "probe_calls": calls, "probe_cache_hits": hits,
                   "service_after": new["service"], "events": events, "stop": scene["stop"],
                   "scene_state": {"path": rel, "sha256": sha256(run / rel)}}
            write_json(sd / "update/update.json", upd)
            if stop:
                final = {**scene, "label": "final"}
                write_json(run / "scene/final-scene-state.json", final)
                files = sorted(str(p.relative_to(run)) for p in (run / "scene").glob("*.json"))
                write_json(run / "freeze/scene-freeze.json", {
                    "schema": "NS1c-scene-freeze-v1", "truth": SP.TRUTH_DERIVED, "frozen_utc": utc(), "code": cs,
                    "statement": "the scene state frozen after the first spread of attention; NS1c stops here",
                    "stop": scene["stop"], "files": {f: sha256(run / f) for f in files}})
    finally:
        write_json(sd / "update/update-opened-files.json", guard_record(g))
    return {"target": t, "service_after": new["service"]["label"], "proposal": new["proposal"],
            "cache_hits": hits, "stop": bool(stop), "events": [[e["event"], e["object"]] for e in events]}


# ------------------------------------------------------------------ the loop driver
def stage_cmd(ctx: Ctx, stage: str, step: int) -> list[str]:
    cmd = [sys.executable, str(HERE / "ns1c_run.py"), stage, "--run", str(ctx.run), "--step", str(step)]
    if ctx.dev:
        cmd.append("--dev")
    if stage == "acquire" and ctx.rehearsal_spp is not None:
        cmd += ["--rehearsal-spp", str(int(ctx.rehearsal_spp))]
    return cmd


def loop(ctx: Ctx, max_steps: int | None = None) -> dict:
    run = ctx.run
    need(run / SP.scene_state_rel("initial"), "initial-probe")
    if (run / "scene/final-scene-state.json").exists() or (run / "scene/terminal.json").exists():
        raise Refused(f"{PREFIX} REFUSED the run has stopped (final scene state or terminal decision exists)")
    require_committed(ctx, "loop")
    t0 = time.time()
    steps, durations = [], []
    rel, sc = latest_scene(run)
    k = int(sc["global_step"]) + 1
    while True:
        if (run / "scene/final-scene-state.json").exists() or (run / "scene/terminal.json").exists():
            break
        if max_steps is not None and len(steps) >= max_steps:
            break
        ts = time.time()
        for stage in SP.STEP:
            p = subprocess.run(stage_cmd(ctx, stage, k), cwd=REPO)
            if p.returncode != 0:
                raise SystemExit(f"{PREFIX} STOP the loop: stage {stage} of step {k} exited {p.returncode}")
            if stage == "schedule":
                d = read_json(run / SP.step_dir(k) / "plan/decision.json")
                if d["kind"] != "attend":
                    break
        dt_s = time.time() - ts
        d = read_json(run / SP.step_dir(k) / "plan/decision.json")
        if d["kind"] != "attend":
            steps.append({"step": k, "kind": d["kind"], "seconds": round(dt_s, 1)})
            break
        durations.append(dt_s)
        sc = read_json(run / SP.scene_state_rel(f"after-step-{k:02d}"))
        steps.append({"step": k, "target": d["action"]["target"], "reason": d["scheduler_reason"],
                      "seconds": round(dt_s, 1), "stopped": sc["stopped"]})
        print(f"{PREFIX} loop step {k}: target {d['action']['target']} ({d['scheduler_reason']}) "
              f"{dt_s:.1f} s; stopped {sc['stopped']}", flush=True)
        if sc["stopped"]:
            break
        mean = float(np.mean(durations))
        projected = (time.time() - t0) + (int(sc["cap"]) - int(sc["executed_actions"])) * mean
        if projected > SP.STEP_BUDGET_PROJECTION_S:
            write_json(run / f"loop/budget-stop-after-step-{k:02d}.json", {
                "schema": "NS1c-budget-stop-v1", "step": k, "mean_step_seconds": mean, "projected_seconds": projected,
                "budget_seconds": SP.STEP_BUDGET_PROJECTION_S, "statement": "STOP before the next step (contract "
                                                                           "section 18); continuation only by Luiz"})
            raise SystemExit(f"{PREFIX} STOP the budget projection {projected:.0f} s exceeds "
                             f"{SP.STEP_BUDGET_PROJECTION_S:.0f} s after step {k}")
        k += 1
    return {"steps": steps, "seconds": round(time.time() - t0, 1),
            "final": (run / "scene/final-scene-state.json").exists(), "terminal": (run / "scene/terminal.json").exists()}


# ------------------------------------------------------------------ visuals and manifest
def visualize(ctx: Ctx, vis: Path) -> dict:
    run = ctx.run
    need(run / SP.scene_state_rel("initial"), "initial-probe")
    import ns1c_visuals as V
    man = V.visualize(run, vis)
    write_manifest(run)
    return {k: v["sha256"] for k, v in man["figures"].items()}


def write_manifest(run: Path) -> dict:
    files = sorted(str(p.relative_to(run)) for p in run.rglob("*") if p.is_file()
                   and p.name not in ("manifest.json", "check-summary.json", "process-log.jsonl"))
    m = {"schema": "NS1c-manifest-v1", "experiment": SP.EXPERIMENT, "contract": SP.CONTRACT, "code": code_state(),
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
    ap.add_argument("--rehearsal-spp", type=int, default=None, help="loop / acquire --dev only: factory-startup rehearsal")
    ap.add_argument("--max-steps", type=int, default=None, help="loop --dev only: stop the rehearsal loop early")
    a = ap.parse_args(argv)
    if (a.command in SP.STEP) != (a.step is not None):
        raise SystemExit(f"{PREFIX} --step is required by, and only by, the step stages")
    if a.dev_scene is not None and (a.command != "eligibility" or not a.dev):
        raise SystemExit(f"{PREFIX} --dev-scene is an `eligibility --dev` option only")
    if a.rehearsal_spp is not None and (a.command not in ("loop", "acquire") or not a.dev):
        raise SystemExit(f"{PREFIX} --rehearsal-spp is a `loop --dev` / `acquire --dev` option only")
    if a.max_steps is not None and (a.command != "loop" or not a.dev):
        raise SystemExit(f"{PREFIX} --max-steps is a `loop --dev` option only")
    scene = [int(x) for x in a.dev_scene.split(",")] if a.dev_scene else None
    ctx = Ctx(a.run, a.dev, a.step, scene, a.rehearsal_spp)
    t0 = time.time()
    fns = {"source": source, "synthetic": synthetic, "eligibility": eligibility, "charts": charts,
           "contexts": contexts, "initial-probe": initial_probe, "schedule": schedule, "preflight": preflight,
           "acquire": acquire, "freeze-observation": freeze_observation,
           "perfect-correspondence": perfect_correspondence, "freeze-correspondence": freeze_correspondence,
           "spherical-geometry": spherical_geometry, "freeze-geometry": freeze_geometry,
           "local-oracle-segmentation": local_oracle_segmentation, "fuse": fuse, "update": update,
           "loop": lambda c: loop(c, a.max_steps),
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
