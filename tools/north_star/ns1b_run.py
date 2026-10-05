"""North Star-1b: recentered local-controller handoff, one action (run order, truth boundary, process contract).

Contract: docs/north-star/ns1b-recentered-controller-handoff-contract.md.

    .venv/bin/python tools/north_star/ns1b_run.py source                     --run RUN
    .venv/bin/python tools/north_star/ns1b_run.py synthetic                  --run RUN
    .venv/bin/python tools/north_star/ns1b_run.py select                     --run RUN
    .venv/bin/python tools/north_star/ns1b_run.py chart                      --run RUN
    .venv/bin/python tools/north_star/ns1b_run.py covariance                 --run RUN   # batch
    .venv/bin/python tools/north_star/ns1b_run.py context                    --run RUN
    .venv/bin/python tools/north_star/ns1b_run.py probe                      --run RUN   # decides Case A / 3 / B
    # Case B only:
    .venv/bin/python tools/north_star/ns1b_run.py preflight                  --run RUN   # Blender, NO render
    .venv/bin/python tools/north_star/ns1b_run.py acquire                    --run RUN   # Blender, the one render
    .venv/bin/python tools/north_star/ns1b_run.py freeze-observation         --run RUN
    .venv/bin/python tools/north_star/ns1b_run.py perfect-correspondence     --run RUN
    .venv/bin/python tools/north_star/ns1b_run.py freeze-correspondence      --run RUN
    .venv/bin/python tools/north_star/ns1b_run.py spherical-geometry         --run RUN
    .venv/bin/python tools/north_star/ns1b_run.py freeze-geometry            --run RUN
    .venv/bin/python tools/north_star/ns1b_run.py local-oracle-segmentation  --run RUN
    .venv/bin/python tools/north_star/ns1b_run.py fuse                       --run RUN
    .venv/bin/python tools/north_star/ns1b_run.py post-probe                 --run RUN
    # always:
    .venv/bin/python tools/north_star/ns1b_run.py visualize                  --run RUN --visuals VIS

Every canonical stage runs once, from a clean pushed commit, under the accepted ``nb1a_guard.OpenGuard`` allowlist
(except ``synthetic``, which reads no data).  No stage opens a catalog, an object name, the Controller-01 bootstrap seeds,
an evaluation file or future visibility.  ``--dev`` runs a stage on a scratch development run (never the canonical RUN)
from a dirty tree; ``select --dev --dev-target K`` rehearses on a NON-candidate entity; ``acquire --dev
--rehearsal-spp N`` renders the synthetic factory-startup rehearsal instead of Classroom.
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

import ns1b_spec as SP  # noqa: E402
from nb1a_guard import OpenGuard  # noqa: E402  (accepted, read-only)

PREFIX = "[ns1b]"
TRUTH_CLASSES = {
    "ORACLE INPUT": "the saved NS1a initialization look and the one new rendered observation; the ORACLE AID (Position, "
                    "Object Index) used by the perfect correspondence services and the local segmentation aid",
    "DERIVED": "the selection, the policy chart, the covariance known answers, the controller context, the probes, the "
               "gate, the world-gaze mapping, the truth-stripped correspondence, the spherical geometry, the local "
               "identity attachment and the H0 fusion",
    "REFERENCE / EVALUATION": "the sealed instance catalog of the new observation (never opened by any NS1b stage)",
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
    def __init__(self, run: Path, dev: bool, dev_target: int | None = None) -> None:
        self.run, self.dev, self.dev_target = run.resolve(), dev, dev_target
        if dev and self.run == SP.RUN_DEFAULT.resolve():
            raise SystemExit(f"{PREFIX} STOP --dev never runs on the canonical RUN")
        if dev_target is not None and not dev:
            raise SystemExit(f"{PREFIX} STOP --dev-target is a development rehearsal option only")

    def p(self, rel: str) -> Path:
        return self.run / rel


def log_process(ctx: Ctx, command: str, t0: float, status: str, extra: dict | None = None) -> None:
    ctx.run.mkdir(parents=True, exist_ok=True)
    entry = {"command": command, "argv": sys.argv, "executable": sys.executable, "code": code_state(),
             "dev": ctx.dev, "finished_utc": utc(), "seconds": round(time.time() - t0, 3), "status": status,
             **(extra or {})}
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


def single_action(decision: dict) -> list[dict]:
    """The process contract: Case B carries exactly one action; Cases A and 3 carry none (anything else refused)."""
    acts = list(decision.get("actions", []))
    if decision.get("case") == "B" and len(acts) == 1:
        return acts
    if decision.get("case") in ("A", "3") and not acts:
        return acts
    raise Refused(f"{PREFIX} REFUSED the decision must be Case B with exactly one action or Case A / 3 with none: "
                  f"case {decision.get('case')!r}, {len(acts)} actions")


def require_case_b(ctx: Ctx, what: str) -> dict:
    need(ctx.p("probe/decision.json"), "probe")
    d = read_json(ctx.p("probe/decision.json"))
    acts = single_action(d)
    if d["case"] != "B":
        raise Refused(f"{PREFIX} REFUSED {what} is not applicable: Case {d['case']} ({d['outcome_reading']}); no "
                      f"physical action exists")
    return {**d, "action": acts[0]}


def forbidden(path: str) -> bool:
    p = str(path)
    return any(t in p for t in SP.FORBIDDEN) or (str(SP.C01_RUN) in p and p.endswith(
        ("actions.json", "result.json", "manifest.json")))


def guard_record(g: OpenGuard, extra: dict | None = None) -> dict:
    rec = g.record()
    rec["modules_loaded"] = {m: m in sys.modules for m in ("cv2", "fsg_stereo", "ab1a_stereo", "ab1d_match",
                                                           "ab1d3_sgbm", "ab1b_oracle", "fsg6f_frontier",
                                                           "fov3d.control.integrated", "fov3d.control.controller02")}
    rec["violations_count"] = len(rec["violations"])
    rec["forbidden_reads"] = sorted({e["path"] for e in rec["events"] if e.get("event") == "open" and forbidden(e["path"])})
    rec.update(extra or {})
    return rec


def verify_record_hashes(run: Path, freeze_rel: str) -> dict:
    fz = read_json(run / freeze_rel)
    bad = {f: h for f, h in fz["files"].items() if sha256(run / f) != h}
    if bad:
        raise SystemExit(f"{PREFIX} STOP files changed after {freeze_rel}: {sorted(bad)[:5]}")
    return fz


def ns1a(rel: str) -> Path:
    return SP.NS1A_RUN / rel


def head_pose(c: dict) -> tuple[np.ndarray, np.ndarray]:
    return np.asarray(c["head_R_wh"], np.float64), np.asarray(c["head_origin_w_m"], np.float64)


# ------------------------------------------------------------------ source
def accepted_constants() -> dict:
    import fsg6f_public as PUB
    from fov3d.experiments.classroom_oracle import config as public
    from fov3d.reconstruction import association
    import tools.classroom_oracle1_epistemic  # noqa: F401
    got = {"SURFACE_FRONTIER": dict(PUB.SURFACE_FRONTIER), "FSG6F_FUSION": dict(PUB.FUSION),
           "FSG6F_OBJECT_ID": int(PUB.OBJECT_ID), "FSG6F_VERGENCE_M": float(PUB.VERGENCE_DISTANCE_M),
           "CYCLOPEAN_GRID_DEG": float(public.CYCLOPEAN_GRID_DEG),
           "MIN_INITIAL_TARGET_POINTS": int(public.MIN_INITIAL_TARGET_POINTS), "FUSION": dict(public.FUSION),
           "SURFACE_ASSOCIATION_RADIUS_M": float(association.SURFACE_ASSOCIATION_RADIUS_M)}
    want = {"SURFACE_FRONTIER": SP.SURFACE_FRONTIER, "FSG6F_FUSION": SP.FSG6F_FUSION,
            "FSG6F_OBJECT_ID": SP.FSG6F_OBJECT_ID, "FSG6F_VERGENCE_M": SP.FSG6F_VERGENCE_M,
            "CYCLOPEAN_GRID_DEG": SP.CYCLOPEAN_GRID_DEG, "MIN_INITIAL_TARGET_POINTS": SP.MIN_POINTS,
            "FUSION": {"association_radius_m": SP.ASSOCIATION_RADIUS_M, "hash_cell_m": SP.HASH_CELL_M},
            "SURFACE_ASSOCIATION_RADIUS_M": SP.ASSOCIATION_RADIUS_M}
    if got != want:
        raise SystemExit(f"{PREFIX} STOP the accepted policy constants differ: {got} != {want}")
    return got


def source(ctx: Ctx) -> dict:
    run = ctx.run
    once(run / "source/source-manifest.json", "the source record")
    cs = require_committed(ctx, "source")
    origin = git("remote", "get-url", "origin")
    anc = {name: subprocess.run(["git", "merge-base", "--is-ancestor", sha, "HEAD"], cwd=REPO).returncode == 0
           for name, sha in (("base", SP.BASE_COMMIT), ("ns1a_acceptance", SP.NS1A_ACCEPTANCE),
                             ("contract", SP.CONTRACT_COMMIT))}
    contract_unchanged = subprocess.run(["git", "diff", "--quiet", SP.CONTRACT_COMMIT, "--", SP.CONTRACT],
                                        cwd=REPO).returncode == 0
    if SP.CANONICAL_REMOTE not in origin or not all(anc.values()) or not contract_unchanged:
        raise SystemExit(f"{PREFIX} STOP provenance: origin {origin}; ancestors {anc}; contract unchanged "
                         f"{contract_unchanged}")
    import ns1b_chart as CH
    CH.ensure_policy_modules()
    consts = accepted_constants()
    obs6 = [ns1a(SP.ns1a_obs(SP.EXPECTED_RANK, d, n)) for d, n in (("acquisition", "calibration.json"),
                                                                    ("acquisition", "rgb-observation.npz"),
                                                                    ("oracle_aid", "reference-observation.npz"))]
    reads = [ns1a(f) for f in SP.NS1A_FREEZES] + [ns1a(SP.NS1A_SEED_SET), ns1a(SP.NS1A_MAPS), ns1a(SP.NS1A_GAZE_LIST),
                                                  ns1a(SP.NS1A_ACQ_RUN)]
    g = OpenGuard("ns1b-source", reads, [run / "source"])
    try:
        with g:
            pins = {p: sha256(REPO / p) for p in SP.SOURCE_PINS}
            bad = {p: h for p, h in pins.items() if h != SP.SOURCE_PINS[p]}
            if bad:
                raise SystemExit(f"{PREFIX} STOP accepted sources changed: {bad}")
            handoff = {}
            for rel, want in [*SP.NS1A_FREEZES.items(), (SP.NS1A_SEED_SET, SP.NS1A_SEED_SET_SHA256),
                              (SP.NS1A_MAPS, SP.NS1A_MAPS_SHA256), (SP.NS1A_GAZE_LIST, SP.NS1A_GAZE_LIST_SHA256),
                              (SP.NS1A_ACQ_RUN, SP.NS1A_ACQ_RUN_SHA256)]:
                h = sha256(ns1a(rel))
                if h != want:
                    raise SystemExit(f"{PREFIX} STOP NS1a {rel} changed: {h} != {want}")
                handoff[rel] = h
            sfz = read_json(ns1a("freeze/seed-set-freeze.json"))
            ofz = read_json(ns1a("freeze/observation-freeze.json"))
            if sfz["files"].get(SP.NS1A_SEED_SET) != SP.NS1A_SEED_SET_SHA256 or \
                    sfz["files"].get(SP.NS1A_MAPS) != SP.NS1A_MAPS_SHA256:
                raise SystemExit(f"{PREFIX} STOP the NS1a seed freeze does not carry the pinned seed set / maps")
            if read_json(ns1a(SP.NS1A_ACQ_RUN))["catalog_seal"]["sha256"] != SP.NS1A_CATALOG_SEAL:
                raise SystemExit(f"{PREFIX} STOP the NS1a catalog seal differs")
            summary = {"schema": "NS1b-source-v1", "experiment": SP.EXPERIMENT, "code": cs, "origin": origin,
                       "ancestors": anc, "contract": SP.CONTRACT, "contract_commit": SP.CONTRACT_COMMIT,
                       "contract_unchanged": contract_unchanged, "base_commit": SP.BASE_COMMIT,
                       "ns1a_acceptance": SP.NS1A_ACCEPTANCE, "source_pins": pins, "accepted_constants": consts,
                       "ns1a_handoff": handoff, "ns1a_catalog_seal": SP.NS1A_CATALOG_SEAL,
                       "ns1a_observation_freeze_files": {str(p.relative_to(SP.NS1A_RUN)): ofz["files"][
                           str(p.relative_to(SP.NS1A_RUN))] for p in obs6},
                       "adapter_substitutions": [list(s) for s in SP.ADAPTER_SUBSTITUTIONS]}
            write_json(run / "source/source-manifest.json", summary)
    finally:
        write_json(run / "source/source-opened-files.json", guard_record(g))
    return {"pins": len(pins), "handoff": len(handoff)}


# ------------------------------------------------------------------ synthetic known answers
def synthetic(ctx: Ctx) -> dict:
    run = ctx.run
    need(run / "source/source-manifest.json", "source")
    once(run / "synthetic/synthetic-report.json", "the synthetic known answers")
    require_committed(ctx, "synthetic")
    import ns1b_synthetic as SY
    rep = SY.run_all()
    write_json(run / "synthetic/synthetic-report.json", rep)
    if rep["failed"]:
        raise SystemExit(f"{PREFIX} STOP synthetic known answers failed (Outcome 4): {rep['failed']}")
    return {"passed": rep["count"] - len(rep["failed"]), "count": rep["count"], "marker": rep["marker"]}


# ------------------------------------------------------------------ section 5: target selection
def select(ctx: Ctx) -> dict:
    run = ctx.run
    rep = read_json(run / "synthetic/synthetic-report.json") if (run / "synthetic/synthetic-report.json").exists() else {}
    if rep.get("failed") != []:
        raise Refused(f"{PREFIX} REFUSED the synthetic known answers must pass first")
    once(run / "selection/target-selection.json", "the target selection")
    cs = require_committed(ctx, "select")
    import ns1b_core as CORE
    reads = [ns1a(SP.NS1A_SEED_SET), ns1a("freeze/seed-set-freeze.json"), ns1a(SP.NS1A_GAZE_LIST)]
    g = OpenGuard("ns1b-select", reads, [run / "selection"])
    try:
        with g:
            for rel, want in ((SP.NS1A_SEED_SET, SP.NS1A_SEED_SET_SHA256), (SP.NS1A_GAZE_LIST, SP.NS1A_GAZE_LIST_SHA256),
                              ("freeze/seed-set-freeze.json", SP.NS1A_FREEZES["freeze/seed-set-freeze.json"])):
                if sha256(ns1a(rel)) != want:
                    raise SystemExit(f"{PREFIX} STOP NS1a {rel} changed")
            sel = CORE.select_target(read_json(ns1a(SP.NS1A_SEED_SET)), read_json(ns1a(SP.NS1A_GAZE_LIST)))
            out = {"schema": "NS1b-selection-v1", "truth": SP.TRUTH_DERIVED, "code": cs,
                   "statement": "deterministic target selection from the frozen NS1a seed set, gaze provenance and the "
                                "accepted sensor geometry only; no name, catalog, Controller-01 result, probe, future "
                                "visibility or render", **sel,
                   "expected_from_mandate": {"temporary_entity_id": SP.EXPECTED_TARGET, "rank": SP.EXPECTED_RANK},
                   "matches_expectation": sel["selected"] == SP.EXPECTED_TARGET
                   and sel["selected_rank"] == SP.EXPECTED_RANK}
            if ctx.dev_target is not None:
                cand = {int(r["temporary_entity_id"]) for r in sel["candidates"]}
                if int(ctx.dev_target) in cand:
                    raise SystemExit(f"{PREFIX} STOP the development rehearsal must use a NON-candidate entity")
                ent = next(e for e in read_json(ns1a(SP.NS1A_SEED_SET))["entities"]
                           if int(e["temporary_entity_id"]) == int(ctx.dev_target))
                r = int(ent["initialized_at_rank"])
                y, p = next((y, p) for rr, y, p in SP.NS1A_RANK_GAZES if rr == r)
                import ns1b_chart as CH
                out.update({"DEV_OVERRIDE": True, "rule_selected": sel["selected"], "selected": int(ctx.dev_target),
                            "selected_rank": r, "selected_gaze_deg": [y, p],
                            "selected_leverage": CH.leverage(CH.gaze_direction(y, p)), "decided_by": "DEV_OVERRIDE"})
            write_json(run / "selection/target-selection.json", out)
    finally:
        write_json(run / "selection/selection-opened-files.json", guard_record(g))
    if not out["matches_expectation"] and ctx.dev_target is None:
        raise SystemExit(f"{PREFIX} STOP the rule selected entity {sel['selected']} at rank {sel['selected_rank']}, "
                         f"not the expected {SP.EXPECTED_TARGET} at rank {SP.EXPECTED_RANK} (discrepancy recorded)")
    return {"selected": out["selected"], "rank": out["selected_rank"], "decided_by": out["decided_by"],
            "leverage": out["selected_leverage"]}


# ------------------------------------------------------------------ section 6: the policy chart
def chart(ctx: Ctx) -> dict:
    run = ctx.run
    need(run / "selection/target-selection.json", "select")
    once(run / "chart/policy-chart.json", "the policy chart")
    cs = require_committed(ctx, "chart")
    import ns1b_chart as CH
    g = OpenGuard("ns1b-chart", [run / "selection/target-selection.json"], [run / "chart"])
    try:
        with g:
            sel = read_json(run / "selection/target-selection.json")
            y, p = sel["selected_gaze_deg"]
            g0 = CH.gaze_direction(y, p)
            try:
                basis = CH.chart_basis(g0)
            except CH.ChartSingular as exc:
                write_json(run / "chart/policy-chart.json", {"schema": "NS1b-chart-v1", "singular": True,
                                                             "error": str(exc)})
                raise SystemExit(f"{PREFIX} {exc}")
            r = basis["R_HC"]
            rng = np.random.default_rng(int(sel["selected"]))
            pts = g0[None] * rng.uniform(1.0, 5.0, (64, 1)) + rng.normal(scale=0.3, size=(64, 3))
            checks = CH.chart_checks(r, g0, pts)
            if not checks["ok"]:
                raise SystemExit(f"{PREFIX} STOP the chart fails its requirements (Outcome 4): {checks}")
            up_h0 = basis["y_C_in_H0"]
            out = {"schema": "NS1b-chart-v1", "truth": SP.TRUTH_DERIVED, "code": cs, "label": SP.LABEL_CHART,
                   "statement": "a TEMPORARY POLICY COORDINATE CHART centred on the target's initialization gaze; NOT "
                                "physical head motion; the physical head stays fixed in canonical H0",
                   "target": sel["selected"], "seed_gaze_H0_deg": [y, p], "g0_H0": g0.tolist(),
                   "construction": "x_C = normalize(b - (b.g0) g0), z_C = -g0, y_C = normalize(z_C x x_C); b = +X",
                   "R_HC": r.tolist(), "x_C_in_H0": basis["x_C_in_H0"].tolist(), "y_C_in_H0": up_h0.tolist(),
                   "z_C_in_H0": basis["z_C_in_H0"].tolist(), "projected_baseline_norm": basis["projected_baseline_norm"],
                   "b_dot_g0": basis["b_dot_g0"], "leverage": CH.leverage(g0), "checks": checks,
                   "chart_up_dot_world_up": float(up_h0[1]),
                   "local_domain_deg": {"yaw": [SP.SURFACE_FRONTIER["yaw_min_deg"], SP.SURFACE_FRONTIER["yaw_max_deg"]],
                                        "pitch": [SP.SURFACE_FRONTIER["pitch_min_deg"],
                                                  SP.SURFACE_FRONTIER["pitch_max_deg"]],
                                        "step": SP.SURFACE_FRONTIER["component_step_deg"]},
                   "domain_corners_in_H0_deg": [list(CH.local_to_world_gaze(a, b, r)[:2])
                                                for a, b in ((-25, -20), (25, -20), (25, 20), (-25, 20))]}
            write_json(run / "chart/policy-chart.json", out)
    finally:
        write_json(run / "chart/chart-opened-files.json", guard_record(g))
    return {"target": out["target"], "projected_baseline_norm": out["projected_baseline_norm"],
            "orthonormality_error": checks["orthonormality_error"], "seed_local": checks["seed_local_yaw_pitch_deg"]}


# ------------------------------------------------------------------ section 8: covariance
def fixture_files() -> list[Path]:
    """Every accepted Controller-01 / 02 file the replay fixtures read (listed before the guard; name-free)."""
    files = sorted((SP.C01_RUN / "objects").glob("instance_*/trajectory.partial.json"))
    rows = []
    for f in files:
        obj = int(f.parent.name.split("_")[1])
        rows += [(obj, int(t["step"]), int(t["global_step"])) for t in read_json(f)]
    last = max(int(SP.K_FIXTURES[k]["after_global_step"]) for k in SP.K_FIXTURES)
    objs = {int(SP.K_FIXTURES[k]["object"]) for k in SP.K_FIXTURES}
    for obj, k, s in rows:
        if s <= last:
            files.append(SP.C01_RUN / f"objects/instance_{obj:04d}/patches/fix_{k:02d}.npz")
            if obj in objs:
                a = SP.C01_RUN / f"objects/instance_{obj:04d}/acquisitions/fix_{k:02d}"
                files += [a / "calibration.json", a / "oracle_observation.npz"]
    return sorted(set(files)) + [SP.C02_RUN / SP.C02_FINAL_RESIDUE]


def covariance(ctx: Ctx) -> dict:
    run = ctx.run
    need(run / "chart/policy-chart.json", "chart")
    once(run / "covariance/covariance-report.json", "the covariance known answers")
    cs = require_committed(ctx, "covariance")
    import ns1b_chart as CH
    import ns1b_core as CORE
    import ns1b_fixtures as FX
    CH.ensure_policy_modules()
    import ns1a_core  # noqa: F401
    files = fixture_files()
    traj = FX.trajectory_files()
    sel_rank = int(read_json(run / "selection/target-selection.json")["selected_rank"])
    cal_p = ns1a(SP.ns1a_obs(sel_rank, "acquisition", "calibration.json"))
    reads = files + [run / "chart/policy-chart.json", run / "selection/target-selection.json", cal_p]
    g = OpenGuard("ns1b-covariance", reads, [run / "covariance"])
    t0 = time.time()
    try:
        with g:
            ch = read_json(run / "chart/policy-chart.json")
            r = np.asarray(ch["R_HC"], np.float64)
            analytic = FX.analytic_suite()
            replay = FX.replay_suite(include_k4=True, traj_files=traj)
            # 8c on the canonical chart: the real initialization calibration (calibration only, no scene data) and
            # two predicted looks of the real fixed-head sensor at the world gazes of local candidates
            cal0 = read_json(cal_p)
            hr, ho = head_pose(cal0)
            g0 = np.asarray(ch["g0_H0"], np.float64)
            rng = np.random.default_rng(7)
            pts = g0[None] * rng.uniform(2.0, 4.5, (40, 1)) + rng.normal(scale=0.08, size=(40, 3))
            cals = [cal0] + [CH.north_star_sensor(SP.PROFILE, *CH.local_to_world_gaze(a, b, r)[:2], hr, ho)
                             for a, b in ((5.0, 5.0), (-5.0, 0.0))]
            canon = FX.projection_invariance(cals, r, pts)
            digest_ok = replay["files_digest"] == SP.C01_FIXTURE_DIGEST
            parts = {**{k: v["pass"] for k, v in analytic.items()},
                     **{k: replay[k]["pass"] for k in ("K2", "K3", "K3q", "K4")},
                     "fixture_provenance_digest": digest_ok,
                     "projection_invariance_canonical_chart": canon["pass"]}
            failed = [k for k, v in parts.items() if not v]
            out = {"schema": "NS1b-covariance-v1", "truth": SP.TRUTH_DERIVED, "code": cs,
                   "statement": "coordinate covariance of the frame adapter, established before it touches NS1a data: "
                                "identity reproduction (K1 analytic; K2/K3/K3q accepted Controller-01 replay states; "
                                "K4 the accepted Controller-02 verdict), rigid rotations about the physical baseline, "
                                "projection invariance and the gate semantics",
                   "parts": parts, "failed": failed, "analytic": CORE.jsonable(analytic),
                   "replay": CORE.jsonable({k: v for k, v in replay.items()}),
                   "fixture_files_read": int(replay["files_read"]), "fixture_files_digest": replay["files_digest"],
                   "fixture_files_digest_pinned": SP.C01_FIXTURE_DIGEST,
                   "projection_invariance_canonical_chart": CORE.jsonable(canon),
                   "seconds": round(time.time() - t0, 1),
                   "marker": "NS1B_COVARIANCE_PASS" if not failed else "NS1B_COVARIANCE_FAIL"}
            write_json(run / "covariance/covariance-report.json", out)
    finally:
        write_json(run / "covariance/covariance-opened-files.json", guard_record(g))
    if failed:
        raise SystemExit(f"{PREFIX} STOP coordinate covariance failed (Outcome 4; no render): {failed}")
    return {"marker": out["marker"], "parts": len(parts), "seconds": out["seconds"]}


# ------------------------------------------------------------------ section 9: the controller context
def context_reads(run: Path, rank: int) -> list[Path]:
    return [ns1a(SP.ns1a_obs(rank, "acquisition", "calibration.json")),
            ns1a(SP.ns1a_obs(rank, "acquisition", "rgb-observation.npz")),
            ns1a(SP.ns1a_obs(rank, "oracle_aid", "reference-observation.npz")),
            ns1a("freeze/observation-freeze.json"), ns1a("freeze/seed-set-freeze.json"), ns1a(SP.NS1A_MAPS),
            run / "selection/target-selection.json", run / "chart/policy-chart.json",
            run / "covariance/covariance-report.json"]


def context(ctx: Ctx) -> dict:
    run = ctx.run
    need(run / "covariance/covariance-report.json", "covariance")
    if read_json(run / "covariance/covariance-report.json").get("failed") != []:
        raise Refused(f"{PREFIX} REFUSED coordinate covariance must pass first")
    once(run / "context/context.json", "the controller context")
    cs = require_committed(ctx, "context")
    import ns1b_chart as CH
    import ns1b_core as CORE
    CH.ensure_policy_modules()
    sel = read_json(run / "selection/target-selection.json")
    k, rank = int(sel["selected"]), int(sel["selected_rank"])
    (run / "context").mkdir(parents=True, exist_ok=True)
    g = OpenGuard("ns1b-context", context_reads(run, rank), [run / "context"])
    try:
        with g:
            ofz, sfz = read_json(ns1a("freeze/observation-freeze.json")), read_json(ns1a("freeze/seed-set-freeze.json"))
            inputs = {}
            for d, n in (("acquisition", "calibration.json"), ("acquisition", "rgb-observation.npz"),
                         ("oracle_aid", "reference-observation.npz")):
                rel = SP.ns1a_obs(rank, d, n)
                h = sha256(ns1a(rel))
                if h != ofz["files"][rel]:
                    raise SystemExit(f"{PREFIX} STOP the NS1a initialization look {rel} changed after its freeze")
                inputs[rel] = h
            if sha256(ns1a(SP.NS1A_MAPS)) != sfz["files"][SP.NS1A_MAPS]:
                raise SystemExit(f"{PREFIX} STOP the NS1a seed maps changed after the seed freeze")
            ch = read_json(run / "chart/policy-chart.json")
            r = np.asarray(ch["R_HC"], np.float64)
            cal = read_json(ns1a(SP.ns1a_obs(rank, "acquisition", "calibration.json")))
            rgb = load_npz(ns1a(SP.ns1a_obs(rank, "acquisition", "rgb-observation.npz")))
            ref = load_npz(ns1a(SP.ns1a_obs(rank, "oracle_aid", "reference-observation.npz")))
            sm = CORE.load_surface_map(load_npz(ns1a(SP.NS1A_MAPS)), k)
            m = CORE.map_arrays(sm)
            want_n = None if ctx.dev else next(e["final_surfels"] for e in sel["candidates"]
                                               if e["temporary_entity_id"] == k)
            if not np.all(m["instance_id"] == k) or (want_n is not None and len(m["xyz_h"]) != want_n):
                raise SystemExit(f"{PREFIX} STOP the target map is not the frozen NS1a map of entity {k}")
            rec, meta, st = CORE.matcher_state(cal, rgb, ref)
            g0 = np.asarray(ch["g0_H0"], np.float64)
            seed_local = CH.yaw_pitch(CH.to_chart(g0, r))
            if max(abs(seed_local[0]), abs(seed_local[1])) > SP.CENTRE_TOL_DEG:
                raise SystemExit(f"{PREFIX} STOP the seed gaze is not local (0, 0): {seed_local}")
            c_ctx, ad = CORE.build_context(k, cal, st, rec["valid"], r, (0.0, 0.0))
            hr, ho = head_pose(cal)
            fixed = CORE.fixed_head(cal, hr, ho)
            if not fixed["ok"] or list(cal["gaze_yaw_pitch_deg"]) != list(sel["selected_gaze_deg"]):
                raise SystemExit(f"{PREFIX} STOP the initialization calibration is not the fixed head at the seed gaze")
            rc = np.asarray(cal["eyes"][0]["R_hc"], np.float64)
            ang = lambda a, b: float(np.degrees(np.arccos(np.clip(np.dot(a, b), -1.0, 1.0))))  # noqa: E731
            ev = CORE.evidence_arrays(c_ctx)
            np.savez_compressed(run / "context/controller-state.npz", ids_left=st["ids_left"], ids_right=st["ids_right"],
                                raw_support_L=st["raw_support_L"], raw_support_R=st["raw_support_R"],
                                matcher_valid=np.asarray(rec["valid"], bool))
            np.savez_compressed(run / "context/evidence.npz", **ev)
            np.savez_compressed(run / "context/target-map-H0.npz", **m)
            out = {"schema": "NS1b-context-v1", "truth": SP.TRUTH_DERIVED, "code": cs,
                   "statement": "the accepted LocalPolicyContext of the selected entity from its frozen NS1a handoff: "
                                "the NS1a H0 map (NORTH-STAR METRIC MAP, authoritative) and the saved initialization look "
                                "through the accepted Classroom matcher (CONTROLLER OBSERVATION STATE only); no "
                                "rerender, no catalog, no name",
                   "target": k, "initialization_rank": rank, "inputs": inputs,
                   "ns1a_maps_sha256": sha256(ns1a(SP.NS1A_MAPS)),
                   "map": {"surfels": int(len(m["xyz_h"])), "patch_ids": [str(x) for x in m["patch_ids"]],
                           "frame": SP.LABEL_H0, "all_ids_target": bool(np.all(m["instance_id"] == k)),
                           "z_H0_positive_fraction": float((m["xyz_h"][:, 2] > 0).mean()),
                           "local_forward_fraction": float((CH.to_chart(m["xyz_h"], r)[:, 2] < -1e-6).mean())},
                   "matcher": CORE.jsonable(meta),
                   "matcher_target_valid_points": int((np.asarray(rec["valid"], bool)
                                                       & (np.asarray(rec["instance_id"]) == k)).sum()),
                   "controller_state_target_pixels_L": int((st["ids_left"] == k).sum()),
                   "seed_local_yaw_pitch_deg": list(seed_local), "current_gaze_deg": list(c_ctx.gaze),
                   "visited": [list(v) for v in c_ctx.visited], "own_looks": len(c_ctx.history),
                   "calibration_sha256": inputs[SP.ns1a_obs(rank, "acquisition", "calibration.json")],
                   "calibration_gaze_H0_deg": list(cal["gaze_yaw_pitch_deg"]),
                   "tangent_frame": cal.get("tangent_frame"), "fixed_head": fixed,
                   "evidence_cells": {k2: int(v.sum()) for k2, v in ev.items()}, "adapter": ad,
                   "camera_vs_chart_deg": {"left_image_x_vs_x_C": ang(rc[:, 0], r[:, 0]),
                                           "left_image_up_vs_y_C": ang(-rc[:, 1], r[:, 1])}}
            write_json(run / "context/context.json", out)
    finally:
        write_json(run / "context/context-opened-files.json", guard_record(g))
    return {"target": k, "surfels": out["map"]["surfels"], "own_looks": out["own_looks"],
            "seen_any": out["evidence_cells"]["seen_any"]}


def load_context(run: Path, files: dict | None = None):
    """The context rebuilt from its saved artifacts (no Position read): state, evidence, calibration, map."""
    import ns1b_chart as CH
    import ns1b_core as CORE
    from fov3d.control import object_policy
    from fov3d.experiments.classroom_oracle import controller01 as c01
    cj = read_json(run / "context/context.json")
    stz = load_npz(run / "context/controller-state.npz")
    evz = load_npz(run / "context/evidence.npz")
    rank = int(cj["initialization_rank"])
    cal_p = ns1a(SP.ns1a_obs(rank, "acquisition", "calibration.json"))
    if sha256(cal_p) != cj["calibration_sha256"]:
        raise SystemExit(f"{PREFIX} STOP the initialization calibration changed")
    cal = read_json(cal_p)
    st = {k: stz[k] for k in ("ids_left", "ids_right", "raw_support_L", "raw_support_R")}
    ctx = c01.LocalPolicyContext(int(cj["target"]))
    for k, v in evz.items():
        arr = getattr(ctx.evidence, k)
        if arr.shape != v.shape:
            raise SystemExit(f"{PREFIX} STOP the saved evidence chart shape differs")
        arr[...] = v
    ctx.history.append(object_policy.history_entry(
        calibration=cal, instance_L=st["ids_left"], raw_support_L=st["raw_support_L"], instance_R=st["ids_right"],
        raw_support_R=st["raw_support_R"], target_object_id=int(cj["target"])))
    ctx.visited.append((0.0, 0.0))
    ctx.gaze, ctx.calibration, ctx.state = (0.0, 0.0), cal, st
    sm_arr = load_npz(run / "context/target-map-H0.npz")
    del CH, CORE
    return ctx, cj, cal, st, stz["matcher_valid"], sm_arr


# ------------------------------------------------------------------ section 10: the pre-action probe
def probe_reads(run: Path) -> list[Path]:
    cj = read_json(run / "context/context.json")
    return [run / "context/context.json", run / "context/controller-state.npz", run / "context/evidence.npz",
            run / "context/target-map-H0.npz", run / "chart/policy-chart.json", run / "selection/target-selection.json",
            ns1a(SP.ns1a_obs(int(cj["initialization_rank"]), "acquisition", "calibration.json"))]


def probe(ctx: Ctx) -> dict:
    run = ctx.run
    need(run / "context/context.json", "context")
    once(run / "probe/pre-action-probe.json", "the one pre-action probe")
    cs = require_committed(ctx, "probe")
    import ns1b_chart as CH
    import ns1b_core as CORE
    import ns1a_core
    CH.ensure_policy_modules()
    from fov3d.experiments.classroom_oracle import controller01 as c01
    import fsg6f_frontier as FR
    g = OpenGuard("ns1b-probe", probe_reads(run), [run / "probe"])
    try:
        with g:
            c_ctx, cj, cal, st, valid, m = load_context(run)
            ch = read_json(run / "chart/policy-chart.json")
            r = np.asarray(ch["R_HC"], np.float64)
            g0 = np.asarray(ch["g0_H0"], np.float64)
            hr, ho = head_pose(cal)
            map_h0 = np.asarray(m["xyz_h"], np.float64)
            map_c = CH.to_chart(map_h0, r)
            ctx0 = CORE.copy_ctx(c_ctx)
            out = CORE.probe(c_ctx, map_c, r, CH.north_star_sensor, hr, ho, SP.PROFILE, g0, "pre-action probe")
            case = CORE.case_of(out)
            # diagnostic: the accepted policy WITHOUT the chart on the seed (expected refusal)
            ctx_h0 = CORE.copy_ctx(ctx0)
            ctx_h0.gaze = tuple(map(float, cal["gaze_yaw_pitch_deg"]))
            ctx_h0.visited = [ctx_h0.gaze]
            no_chart = {"map_points_forward_in_H0": int((map_h0[:, 2] < -1e-6).sum()),
                        "seed_gaze_H0_deg": list(ctx_h0.gaze),
                        "statement": "diagnostic only: the accepted policy run directly in H0 (no chart) on the seed"}
            try:
                res_h0, _dec_h0 = c01.probe_local_policy(ctx_h0, map_h0)
                no_chart.update({"refused": False, "state": res_h0.state.value,
                                 "summary": CORE.jsonable(dict(res_h0.detail))})
            except Exception as exc:  # noqa: BLE001  (the accepted code's own refusal is the diagnostic)
                no_chart.update({"refused": True, "error": f"{type(exc).__name__}: {exc}"})
            # invariance: the same context rigidly rotated about the baseline (an exact fixed-head symmetry)
            rotations, inv_ok = [], True
            for beta in SP.PROBE_ROTATIONS_DEG:
                q = CH.rot_x(beta)
                w = CORE.rotate_world(q, cal, map_h0, g0)
                rq = CH.chart_basis(w["g0"])["R_HC"]
                cq, _ad = CORE.build_context(int(cj["target"]), w["calibration"], st, valid, rq, (0.0, 0.0))
                ev_equal = all(np.array_equal(a, b) for a, b in zip(CORE.evidence_arrays(ctx0).values(),
                                                                     CORE.evidence_arrays(cq).values()))
                oq = CORE.probe(cq, CH.to_chart(w["map_h0"], rq), rq, CH.north_star_sensor, hr, ho, SP.PROFILE,
                                w["g0"], f"invariance {beta}")
                diffs, flip = CORE.explain_voxel_flip(CORE.probe_comparison(out, oq), map_c)
                rec = {"beta_deg": beta, "chart_equals_Q_R_HC": float(np.abs(rq - q @ r).max()),
                       "evidence_equal": ev_equal, "differences": diffs, "voxel_boundary_flip": flip,
                       "tie_inversions": CORE.inversions((out["decisions"].get("fsg6f_decision") or {}).get(
                           "candidates", []), (oq["decisions"].get("fsg6f_decision") or {}).get("candidates", []))}
                if out["proposal"] is not None and oq["proposal"] is not None:
                    rec["world_proposal_error"] = float(np.abs(np.asarray(oq["proposal"]["d_H0"])
                                                               - q @ np.asarray(out["proposal"]["d_H0"])).max())
                    pc0 = out["gate"]["detail"].get("predicted_calibration")
                    pcq = oq["gate"]["detail"].get("predicted_calibration")
                    if pc0 and pcq:
                        rec["predicted_calibration_rotated_error"] = max(
                            float(np.abs(np.asarray(e1["R_hc"]) - q @ np.asarray(e0["R_hc"])).max())
                            for e0, e1 in zip(pc0["eyes"], pcq["eyes"]))
                ok = (not diffs and ev_equal and rec["chart_equals_Q_R_HC"] <= 1e-12
                      and rec.get("world_proposal_error", 0.0) <= 1e-12
                      and rec.get("predicted_calibration_rotated_error", 0.0) <= 1e-9)
                rec["pass"] = bool(ok)
                inv_ok &= ok
                rotations.append(rec)
            # Euclidean frame invariance of the 12-mm map resolution on the probe's own frontier targets
            fr = FR.extract_frontier(map_c, 0.0, 0.0, cal)
            tc = fr["target_xyz_h"]
            mres_c = FR._target_mapped_mask(tc, map_c)
            mres_h = FR._target_mapped_mask(CH.to_h0(tc, r), map_h0)
            euclid = {"frontier_targets": int(len(tc)), "equal": bool(np.array_equal(mres_c, mres_h)),
                      "mapped_C": int(mres_c.sum()), "mapped_H0": int(mres_h.sum())}
            voxel_pts = CORE.voxel_boundary_points(map_c)
            prop = out["proposal"]
            planned = None
            if prop is not None:
                if prop["roundtrip_error_deg"] > SP.GAZE_ROUNDTRIP_TOL_DEG:
                    raise SystemExit(f"{PREFIX} STOP the chart / world gaze round trip fails (Outcome 4)")
                planned = ns1a_core.planned_calibration(*prop["world_gaze_deg"], hr, ho)
                prop["planned_calibration_test"] = CORE.physical_calibration_test(
                    planned, prop["local_gaze_deg"], r, hr, ho)
                pc = out["gate"]["detail"].get("predicted_calibration")
                prop["gate_predicted_equals_planned"] = None if pc is None else CORE.calibration_matches(pc, planned)
            outcome4 = (not inv_ok) or (not euclid["equal"]) or (prop is not None and not
                                                                 prop["planned_calibration_test"]["ok"])
            reading = {"A": "Outcome 2 - handoff succeeds, selected entity QUIET",
                       "3": "Outcome 3 - policy proposal exists but the adapted Controller-02 gate rejects it",
                       "B": "Case B - one admissible action (Outcome 1 pending its execution)"}[case]
            if outcome4:
                reading = "Outcome 4 - coordinate / adapter failure"
            full = {"schema": "NS1b-pre-action-probe-v1", "truth": SP.TRUTH_DERIVED, "code": cs,
                    "statement": "the ONE read-only pre-action probe: the accepted controller01.probe_local_policy "
                                 "(FSG6f -> Cyclopean) and controller02.final_look_gate_v1 run unchanged on chart-C "
                                 "inputs under the frame adapter; physical projections, calibrations and observability "
                                 "in the fixed-head H0 frame", "target": int(cj["target"]),
                    "policy_configuration_used": CORE.jsonable(_policy_configuration()),
                    "case": case, "outcome_reading": reading, "probe": out, "no_chart_diagnostic": no_chart,
                    "baseline_rotation_invariance": rotations, "euclidean_invariance": euclid,
                    "map_points_on_voxel_boundaries": voxel_pts, "outcome_4": bool(outcome4)}
            write_json(run / "probe/pre-action-probe.json", full)
            actions = []
            if case == "B" and not outcome4:
                b = ns1a_core.calibration_bytes(planned)
                (run / "probe/planned-calibration.json").write_bytes(b)
                actions = [{"index": 1, "target": int(cj["target"]), "source": prop["source"],
                            "local_gaze_deg": prop["local_gaze_deg"], "world_gaze_deg": prop["world_gaze_deg"],
                            "planned_calibration_sha256": hashlib.sha256(b).hexdigest(),
                            "patch_id": SP.ACTION_PATCH_ID}]
            decision = {"schema": "NS1b-decision-v1", "truth": SP.TRUTH_DERIVED, "code": cs,
                        "case": "4" if outcome4 else case, "outcome_reading": reading, "target": int(cj["target"]),
                        "actions": actions, "gate": {k: out["gate"][k] for k in ("admissible", "reason")},
                        "probe_sha256": sha256(run / "probe/pre-action-probe.json")}
            write_json(run / "probe/decision.json", decision)
    finally:
        write_json(run / "probe/probe-opened-files.json", guard_record(g))
    if outcome4:
        raise SystemExit(f"{PREFIX} STOP Outcome 4 (coordinate / adapter failure): invariance {inv_ok}, euclidean "
                         f"{euclid['equal']}; no render")
    return {"case": case, "reading": reading, "state": out["state"],
            "proposal": None if prop is None else {k: prop[k] for k in ("source", "local_gaze_deg", "world_gaze_deg")},
            "gate": decision["gate"]}


def _policy_configuration() -> dict:
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


# ------------------------------------------------------------------ Blender (Case B only)
def blender(ctx: Ctx, args: list[str], log: Path, factory: bool = False) -> None:
    log.parent.mkdir(parents=True, exist_ok=True)
    cmd = [SP.BLENDER, "-b"] + (["--factory-startup"] if factory else [str(REPO / SP.BLEND)])
    cmd += ["--python-exit-code", "1", "-P", str(HERE / "ns1b_render.py"), "--"] + args
    with open(log, "w") as f:
        p = subprocess.run(cmd, cwd=REPO, stdout=f, stderr=subprocess.STDOUT)
    text = log.read_text(errors="replace")
    if p.returncode != 0 or "[ns1b-render] COMPLETE" not in text or "[ns1b-render] FAILED" in text:
        raise SystemExit(f"{PREFIX} STOP Blender failed (exit {p.returncode}); see {log}")


def preflight(ctx: Ctx) -> dict:
    run = ctx.run
    require_case_b(ctx, "preflight")
    once(run / "preflight/preflight.json", "the Classroom preflight")
    require_committed(ctx, "preflight")
    if sha256(REPO / SP.BLEND) != SP.BLEND_SHA256:
        raise SystemExit(f"{PREFIX} STOP the Classroom blend changed")
    blender(ctx, ["--mode", "preflight", "--run", str(run)], run / "preflight/blender.log")
    return {k: v for k, v in read_json(run / "preflight/preflight.json").items() if k in ("rendered", "gaze_H0_deg")}


def acquire(ctx: Ctx, rehearsal_spp: int | None) -> dict:
    run = ctx.run
    d = require_case_b(ctx, "acquire")
    if rehearsal_spp is None:
        need(run / "preflight/preflight.json", "preflight")
        if read_json(run / "preflight/preflight.json").get("rendered") is not False:
            raise SystemExit(f"{PREFIX} STOP the preflight record is not a no-render record")
    elif not ctx.dev:
        raise SystemExit(f"{PREFIX} STOP the rehearsal acquisition is a --dev command")
    once(run / "observation", "the one physical observation (never re-rendered)")
    require_committed(ctx, "acquire")
    if rehearsal_spp is None:
        if sha256(REPO / SP.BLEND) != SP.BLEND_SHA256:
            raise SystemExit(f"{PREFIX} STOP the Classroom blend changed")
        blender(ctx, ["--mode", "canonical", "--run", str(run)], run / "acquisition-blender.log")
    else:
        blender(ctx, ["--mode", "rehearsal", "--run", str(run), "--spp", str(int(rehearsal_spp))],
                run / "acquisition-blender.log", factory=True)
    ar = read_json(run / SP.ACQ_RUN_REL)
    for rel in [f"{SP.OBS_ACQ}/{n}" for n in SP.OBS_ACQ_FILES] + [f"{SP.OBS_AID}/{n}" for n in SP.OBS_AID_FILES]:
        need(run / rel, rel)
    if list(ar["gaze_H0_deg"]) != list(d["action"]["world_gaze_deg"]):
        raise SystemExit(f"{PREFIX} STOP the executed gaze differs from the decision")
    return {"gaze_H0_deg": ar["gaze_H0_deg"], "budget": ar["budget"], "spp": ar["spp"]}


# ------------------------------------------------------------------ freeze-observation
def observation_files() -> list[str]:
    return [SP.ACQ_RUN_REL] + [f"{SP.OBS_ACQ}/{n}" for n in SP.OBS_ACQ_FILES] + [f"{SP.OBS_AID}/{n}"
                                                                                 for n in SP.OBS_AID_FILES]


def freeze_observation(ctx: Ctx) -> dict:
    run = ctx.run
    d = require_case_b(ctx, "freeze-observation")
    need(run / SP.ACQ_RUN_REL, "acquire")
    once(run / "freeze/observation-freeze.json", "the observation freeze")
    cs = require_committed(ctx, "freeze-observation")
    files = observation_files()
    g = OpenGuard("ns1b-freeze-observation", [run / f for f in files] + [run / "probe/planned-calibration.json",
                                                                         run / "probe/decision.json"],
                  [run / "freeze"])
    try:
        with g:
            hashes = {f: sha256(run / f) for f in files}
            ar = read_json(run / SP.ACQ_RUN_REL)
            rec = read_json(run / f"{SP.OBS_ACQ}/acquisition.json")
            problems = []
            for key, rel in (("calibration_sha256", f"{SP.OBS_ACQ}/calibration.json"),
                             ("rgb_observation_sha256", f"{SP.OBS_ACQ}/rgb-observation.npz"),
                             ("reference_observation_sha256", f"{SP.OBS_AID}/reference-observation.npz")):
                if ar[key] != hashes[rel]:
                    problems.append(key)
            if (run / f"{SP.OBS_ACQ}/calibration.json").read_bytes() != \
                    (run / "probe/planned-calibration.json").read_bytes():
                problems.append("calibration bytes != the planned calibration")
            if hashes[f"{SP.OBS_ACQ}/calibration.json"] != d["action"]["planned_calibration_sha256"]:
                problems.append("calibration != the decision's planned calibration")
            if (rec["spp"] != ar["spp"] or rec["render_seeds_lr"] != SP.SEEDS or rec["device"] != SP.DEVICE
                    or rec["settings"]["samples"] != ar["spp"]
                    or list(rec["gaze_yaw_pitch_deg"]) != list(d["action"]["world_gaze_deg"])):
                problems.append("acquisition record")
            if not ctx.dev and (ar["spp"] != SP.SPP or ar["exr_samples_lr"] != {"L": str(SP.SPP), "R": str(SP.SPP)}
                                or ar["catalog_seal"]["sha256"] != SP.NS1A_CATALOG_SEAL):
                problems.append("spp / EXR samples / catalog seal")
            with np.load(run / f"{SP.OBS_ACQ}/rgb-observation.npz") as z:
                if sorted(z.files) != ["rgb_L", "rgb_R"]:
                    problems.append(f"rgb keys {z.files}")
            with np.load(run / f"{SP.OBS_AID}/reference-observation.npz") as z:
                if sorted(z.files) != sorted(("instance_L", "instance_R", "position_w_L", "position_w_R")):
                    problems.append(f"reference keys {z.files}")
            if problems:
                raise SystemExit(f"{PREFIX} STOP observation problems: {problems}")
            fz = {"schema": "NS1b-observation-freeze-v1", "truth": SP.TRUTH_ORACLE, "frozen_utc": utc(), "code": cs,
                  "statement": "the one binocular observation at the mapped H0 gaze; never re-rendered. The sealed "
                               "catalog is NOT opened: its Blender-recorded seal is carried", "spp": ar["spp"],
                  "catalog_seal": ar["catalog_seal"], "files": hashes}
            write_json(run / "freeze/observation-freeze.json", fz)
    finally:
        write_json(run / "freeze/observation-freeze-opened-files.json", guard_record(g))
    return {"files": len(hashes), "spp": ar["spp"]}


# ------------------------------------------------------------------ section 13: PERFECT correspondence -> geometry -> id
CORR_FILES = ("correspondence/oracle-correspondences.npz", "correspondence/oracle-summary.json",
              "correspondence/core-class-map.npz", "correspondence/correspondence-opened-files.json")
GEOM_FILES = ("geometry/left-core-rays.npz", "geometry/epipolar-result.npz", "geometry/geometry-summary.json",
              "geometry/geometry-opened-files.json")
SEG_FILES = ("segmentation/local-identity.npz", "segmentation/identity-summary.json")


def perfect_correspondence(ctx: Ctx) -> dict:
    run = ctx.run
    require_case_b(ctx, "perfect-correspondence")
    need(run / "freeze/observation-freeze.json", "freeze-observation")
    once(run / "correspondence", "the perfect correspondence")
    require_committed(ctx, "perfect-correspondence")
    import ab1b_oracle as O   # accepted AB1b oracle, read-only (imported before the guard)
    import fsg_geometry  # noqa: F401
    import ns1a_core as NCORE
    cal, ref = run / f"{SP.OBS_ACQ}/calibration.json", run / f"{SP.OBS_AID}/reference-observation.npz"
    odir = run / "correspondence"
    odir.mkdir(parents=True, exist_ok=True)
    g = OpenGuard("ns1b-oracle", [cal, ref, run / "freeze/observation-freeze.json"], [odir])
    try:
        with g:
            fz = read_json(run / "freeze/observation-freeze.json")
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
            summary = {"schema": "NS1b-oracle-summary-v1", "truth": SP.TRUTH_DERIVED, "label": SP.LABEL_ORACLE_CORR,
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
    run = ctx.run
    require_case_b(ctx, "freeze-correspondence")
    need(run / "correspondence/oracle-correspondences.npz", "perfect-correspondence")
    once(run / "freeze/correspondence-freeze.json", "the correspondence freeze")
    cs = require_committed(ctx, "freeze-correspondence")
    import ab1b_geometry as BG
    g = OpenGuard("ns1b-freeze-correspondence", [run / f for f in CORR_FILES], [run / "freeze"])
    try:
        with g:
            rec = read_json(run / "correspondence/correspondence-opened-files.json")
            want = {str((run / f"{SP.OBS_ACQ}/calibration.json").resolve()),
                    str((run / f"{SP.OBS_AID}/reference-observation.npz").resolve()),
                    str((run / "freeze/observation-freeze.json").resolve())}
            if (rec["violations"] or set(rec["data_reads"]) != want or rec["modules_loaded"]["cv2"]
                    or rec["modules_loaded"]["fsg_stereo"] or rec["forbidden_reads"]):
                raise SystemExit(f"{PREFIX} STOP the oracle guard record is not clean")
            BG.load_product(run / "correspondence/oracle-correspondences.npz")
            fz = {"schema": "NS1b-correspondence-freeze-v1", "truth": SP.TRUTH_DERIVED, "frozen_utc": utc(), "code": cs,
                  "statement": "the truth-stripped perfect-correspondence product, frozen before the spherical geometry",
                  "files": {f: sha256(run / f) for f in CORR_FILES}}
            write_json(run / "freeze/correspondence-freeze.json", fz)
    finally:
        write_json(run / "freeze/correspondence-freeze-opened-files.json", guard_record(g))
    return {"files": len(CORR_FILES)}


def truth_reads(events: list[dict]) -> dict:
    paths = [e["path"] for e in events if e.get("event") == "open"]
    ref = [p for p in paths if p.endswith("reference-observation.npz") or p.endswith(".exr") or "/oracle_aid/" in p
           or "evaluation_only" in p]
    return {"position_reads": len(ref), "object_index_reads": len(ref),
            "catalog_reads": len([p for p in paths if "catalog" in p])}


def spherical_geometry(ctx: Ctx, probe_fn=None) -> dict:
    run = ctx.run
    require_case_b(ctx, "spherical-geometry")
    if not (run / "freeze/correspondence-freeze.json").exists():   # existence only (no read); hashes in freeze-geometry
        raise Refused(f"{PREFIX} REFUSED freeze-correspondence comes first")
    once(run / "geometry", "the spherical geometry")
    require_committed(ctx, "spherical-geometry")
    import ab1b_geometry as BG   # accepted AB1b geometry, read-only
    import fsg_geometry as FG
    cal, prod_p = run / f"{SP.OBS_ACQ}/calibration.json", run / "correspondence/oracle-correspondences.npz"
    odir = run / "geometry"
    odir.mkdir(parents=True, exist_ok=True)
    g = OpenGuard("ns1b-geometry", [cal, prod_p], [odir])
    try:
        with g:
            if probe_fn is not None:
                probe_fn()
            inputs = {"calibration": {"path": str(cal), "sha256": sha256(cal)},
                      "correspondences": {"path": str(prod_p), "sha256": sha256(prod_p)}}
            c = read_json(cal)
            FG.validate_calibration(c)
            prod = BG.load_product(prod_p)
            rays = BG.left_core_rays(c)
            res = BG.compute_epipolar(c, prod)
            np.savez_compressed(odir / "left-core-rays.npz", **rays)
            np.savez_compressed(odir / "epipolar-result.npz", **res)
            summary = {"schema": "NS1b-geometry-summary-v1", "truth": SP.TRUTH_DERIVED, "label": SP.LABEL_GEOMETRY,
                       "statement": "TRUTH-FREE SPHERICAL EPIPOLAR RECONSTRUCTION (accepted AB1b geometry): the "
                                    "calibration and the frozen truth-stripped product only; canonical fixed-head H0",
                       "geometry": BG.SP.GEOMETRY, "geometry_config_sha256": BG.SP.config_sha256(BG.SP.GEOMETRY),
                       "inputs": inputs, "baseline_m": float(c["ipd_m"]), "focal_px": float(c["eyes"][0]["K"][0][0]),
                       **BG.summarize(c, rays, res)}
            write_json(odir / "geometry-summary.json", summary)
    finally:
        rec = guard_record(g)
        rec.update(truth_reads(rec["events"]))
        write_json(odir / "geometry-opened-files.json", rec)
    return {"triangulated": summary["counts"]["triangulated_epipolar"]}


def freeze_geometry(ctx: Ctx) -> dict:
    run = ctx.run
    require_case_b(ctx, "freeze-geometry")
    need(run / "geometry/epipolar-result.npz", "spherical-geometry")
    once(run / "freeze/geometry-freeze.json", "the geometry freeze")
    cs = require_committed(ctx, "freeze-geometry")
    cfz = run / "freeze/correspondence-freeze.json"
    g = OpenGuard("ns1b-freeze-geometry", [run / f for f in GEOM_FILES + CORR_FILES] + [cfz], [run / "freeze"])
    try:
        with g:
            fzc = verify_record_hashes(run, "freeze/correspondence-freeze.json")
            rec = read_json(run / "geometry/geometry-opened-files.json")
            summ = read_json(run / "geometry/geometry-summary.json")
            prod_rel = "correspondence/oracle-correspondences.npz"
            want = {str((run / f"{SP.OBS_ACQ}/calibration.json").resolve()), str((run / prod_rel).resolve())}
            if (rec["violations"] or set(rec["data_reads"]) != want or any(rec["modules_loaded"][m] for m in (
                    "cv2", "fsg_stereo", "ab1a_stereo", "ab1d_match", "ab1d3_sgbm", "ab1b_oracle", "fsg6f_frontier",
                    "fov3d.control.integrated", "fov3d.control.controller02"))
                    or rec["position_reads"] or rec["object_index_reads"] or rec["catalog_reads"]
                    or summ["inputs"]["correspondences"]["sha256"] != fzc["files"][prod_rel]):
                raise SystemExit(f"{PREFIX} STOP the geometry guard record or input is not clean")
            fz = {"schema": "NS1b-geometry-freeze-v1", "truth": SP.TRUTH_DERIVED, "frozen_utc": utc(), "code": cs,
                  "statement": "the truth-free spherical geometry, frozen before any identity is attached",
                  "correspondence_freeze_sha256": sha256(cfz), "files": {f: sha256(run / f) for f in GEOM_FILES}}
            write_json(run / "freeze/geometry-freeze.json", fz)
    finally:
        write_json(run / "freeze/geometry-freeze-opened-files.json", guard_record(g))
    return {"files": len(GEOM_FILES)}


def local_oracle_segmentation(ctx: Ctx, probe_fn=None) -> dict:
    run = ctx.run
    require_case_b(ctx, "local-oracle-segmentation")
    need(run / "freeze/geometry-freeze.json", "freeze-geometry")
    once(run / "segmentation", "the local oracle segmentation")
    require_committed(ctx, "local-oracle-segmentation")
    import ns1a_core as NCORE
    odir = run / "segmentation"
    odir.mkdir(parents=True, exist_ok=True)
    reads = [run / "freeze/geometry-freeze.json"] + [run / f for f in GEOM_FILES] + [
        run / "correspondence/oracle-correspondences.npz", run / f"{SP.OBS_AID}/reference-observation.npz"]
    g = OpenGuard("ns1b-segmentation", reads, [odir])
    try:
        with g:
            verify_record_hashes(run, "freeze/geometry-freeze.json")
            g.mark("geometry_freeze_verified")
            g.mark("identity_access_begins")
            if probe_fn is not None:
                probe_fn()
            prod = load_npz(run / "correspondence/oracle-correspondences.npz")
            res = read_members(run / "geometry/epipolar-result.npz", ("valid_epi",))
            ref = read_members(run / f"{SP.OBS_AID}/reference-observation.npz", SP.SEGMENTATION_MEMBERS)
            ids = NCORE.attach_identity(prod, res["valid_epi"], ref["instance_L"])
            np.savez_compressed(odir / "local-identity.npz", left_core_row=prod["left_core_row"],
                                left_core_col=prod["left_core_col"], temporary_entity_id=ids,
                                valid=np.asarray(res["valid_epi"], bool))
            summ = {"schema": "NS1b-identity-summary-v1", "truth": SP.TRUTH_DERIVED, "label": SP.LABEL_SEGMENTATION,
                    "statement": "ORACLE SEGMENTATION AID: temporary_entity_id = the left raw-core Object Index at the "
                                 "exact uv_L centre of each valid correspondence; not natural identity; no catalog, no "
                                 "names", "reference_members_read": list(SP.SEGMENTATION_MEMBERS),
                    **NCORE.identity_summary(ids)}
            write_json(odir / "identity-summary.json", summ)
    finally:
        write_json(odir / "segmentation-opened-files.json", guard_record(g, {"reference_members_read":
                                                                              list(SP.SEGMENTATION_MEMBERS)}))
    return {"entities": len(summ["entities"])}


# ------------------------------------------------------------------ section 14: H0 fusion
def fuse(ctx: Ctx) -> dict:
    run = ctx.run
    d = require_case_b(ctx, "fuse")
    need(run / "segmentation/identity-summary.json", "local-oracle-segmentation")
    once(run / "fusion/fusion.json", "the one H0 fusion")
    cs = require_committed(ctx, "fuse")
    import ns1b_core as CORE
    from fov3d.reconstruction import surface_map as SMOD  # noqa: F401
    reads = [run / "freeze/geometry-freeze.json"] + [run / f for f in GEOM_FILES + SEG_FILES] + [
        run / "correspondence/oracle-correspondences.npz", run / f"{SP.OBS_ACQ}/rgb-observation.npz",
        run / "context/target-map-H0.npz", run / "context/context.json", run / "probe/decision.json",
        run / "segmentation/segmentation-opened-files.json"]
    (run / "fusion").mkdir(parents=True, exist_ok=True)
    g = OpenGuard("ns1b-fuse", reads, [run / "fusion"])
    try:
        with g:
            verify_record_hashes(run, "freeze/geometry-freeze.json")
            target = int(d["target"])
            prod = load_npz(run / "correspondence/oracle-correspondences.npz")
            res = read_members(run / "geometry/epipolar-result.npz", ("P_epi", "valid_epi"))
            idn = load_npz(run / "segmentation/local-identity.npz")
            rgb_l = read_members(run / f"{SP.OBS_ACQ}/rgb-observation.npz", ("rgb_L",))["rgb_L"]
            if not (np.array_equal(idn["left_core_row"], prod["left_core_row"])
                    and np.array_equal(idn["valid"], res["valid_epi"])):
                raise SystemExit(f"{PREFIX} STOP identity, product and geometry are not aligned")
            uv = prod["uv_L"].astype(np.int64)
            rgb = rgb_l[uv[:, 1], uv[:, 0]].astype(np.float64)
            patch = CORE.target_patch(res["P_epi"], res["valid_epi"], idn["temporary_entity_id"], rgb, target)
            m_arr = load_npz(run / "context/target-map-H0.npz")
            from fov3d.reconstruction import surface_map as SM
            sm = SM.SurfaceMap(np.asarray(m_arr["xyz_h"], np.float64).copy(), np.asarray(m_arr["rgb"], np.float64).copy(),
                               m_arr["instance_id"].copy(), m_arr["support_count"].copy(),
                               m_arr["provenance_mask"].copy(), [str(p) for p in m_arr["patch_ids"]])
            fused, rec = CORE.fuse_h0(sm, patch, target)
            np.savez_compressed(run / "fusion/target-patch.npz", xyz_h=patch["xyz_h"], rgb=patch["rgb"],
                                instance_id=patch["instance_id"])
            np.savez_compressed(run / "fusion/fused-target-map.npz", **CORE.map_arrays(fused))
            idsum = read_json(run / "segmentation/identity-summary.json")
            out = {"schema": "NS1b-fusion-v1", "truth": SP.TRUTH_DERIVED, "code": cs, "frame": SP.LABEL_H0,
                   "statement": "the target's points of the frozen spherical measurement, fused into its NS1a map with "
                                "the accepted surface map (12 mm / 12 mm) in canonical H0 only, with one exact replay",
                   "target": target, "patch_id": SP.ACTION_PATCH_ID, "valid_correspondences":
                       int(np.asarray(res["valid_epi"], bool).sum()), "entities_in_view": idsum["entities"], **rec}
            write_json(run / "fusion/fusion.json", out)
    finally:
        write_json(run / "fusion/fusion-opened-files.json", guard_record(g))
    return {k: out[k] for k in ("action", "map_before", "measured_points", "matched", "new", "map_after")}


# ------------------------------------------------------------------ section 15: the post-action probe
def post_probe(ctx: Ctx) -> dict:
    run = ctx.run
    d = require_case_b(ctx, "post-probe")
    need(run / "fusion/fusion.json", "fuse")
    once(run / "post/post-action-probe.json", "the one post-action probe")
    cs = require_committed(ctx, "post-probe")
    import ns1b_chart as CH
    import ns1b_core as CORE
    CH.ensure_policy_modules()
    reads = probe_reads(run) + [run / "fusion/fusion.json", run / "fusion/fused-target-map.npz",
                                run / "probe/decision.json", run / "freeze/observation-freeze.json",
                                run / f"{SP.OBS_ACQ}/calibration.json", run / f"{SP.OBS_ACQ}/rgb-observation.npz",
                                run / f"{SP.OBS_AID}/reference-observation.npz"]
    (run / "post").mkdir(parents=True, exist_ok=True)
    g = OpenGuard("ns1b-post-probe", reads, [run / "post"])
    try:
        with g:
            c_ctx, cj, cal0, _st, _valid, _m = load_context(run)
            fz = read_json(run / "freeze/observation-freeze.json")
            for rel in (f"{SP.OBS_ACQ}/calibration.json", f"{SP.OBS_ACQ}/rgb-observation.npz",
                        f"{SP.OBS_AID}/reference-observation.npz"):
                if sha256(run / rel) != fz["files"][rel]:
                    raise SystemExit(f"{PREFIX} STOP {rel} changed after the observation freeze")
            ch = read_json(run / "chart/policy-chart.json")
            r = np.asarray(ch["R_HC"], np.float64)
            g0 = np.asarray(ch["g0_H0"], np.float64)
            hr, ho = head_pose(cal0)
            cal1 = read_json(run / f"{SP.OBS_ACQ}/calibration.json")
            rec1, meta1, st1 = CORE.matcher_state(cal1, load_npz(run / f"{SP.OBS_ACQ}/rgb-observation.npz"),
                                                  load_npz(run / f"{SP.OBS_AID}/reference-observation.npz"))
            ad = CORE.add_look(c_ctx, cal1, st1, rec1["valid"], r, tuple(d["action"]["local_gaze_deg"]))
            fused = load_npz(run / "fusion/fused-target-map.npz")
            map_c = CH.to_chart(np.asarray(fused["xyz_h"], np.float64), r)
            out = CORE.probe(c_ctx, map_c, r, CH.north_star_sensor, hr, ho, SP.PROFILE, g0, "post-action probe")
            if out["proposal"] is not None:
                out["proposal"]["planned_calibration_test"] = CORE.physical_calibration_test(
                    CH.north_star_sensor(SP.PROFILE, *out["proposal"]["world_gaze_deg"], hr, ho),
                    out["proposal"]["local_gaze_deg"], r, hr, ho)
            ev = CORE.evidence_arrays(c_ctx)
            np.savez_compressed(run / "post/controller-state.npz", ids_left=st1["ids_left"], ids_right=st1["ids_right"],
                                raw_support_L=st1["raw_support_L"], raw_support_R=st1["raw_support_R"],
                                matcher_valid=np.asarray(rec1["valid"], bool))
            np.savez_compressed(run / "post/evidence.npz", **ev)
            full = {"schema": "NS1b-post-action-probe-v1", "truth": SP.TRUTH_DERIVED, "code": cs,
                    "statement": "the ONE read-only post-action probe after updating the context with the executed look "
                                 "(Controller-01 observe order) and the fused H0 map; its proposal is NOT executed",
                    "target": int(cj["target"]), "visited": [list(v) for v in c_ctx.visited],
                    "own_looks": len(c_ctx.history), "matcher": CORE.jsonable(meta1),
                    "matcher_target_valid_points": int((np.asarray(rec1["valid"], bool)
                                                        & (np.asarray(rec1["instance_id"]) == int(cj["target"]))).sum()),
                    "evidence_cells": {k: int(v.sum()) for k, v in ev.items()}, "evidence_adapter": ad,
                    "geometry_points": int(len(map_c)), "probe": out, "executed": False,
                    "case": CORE.case_of(out)}
            write_json(run / "post/post-action-probe.json", full)
    finally:
        write_json(run / "post/post-opened-files.json", guard_record(g))
    return {"state": out["state"], "proposal": None if out["proposal"] is None else
            {k: out["proposal"][k] for k in ("source", "local_gaze_deg", "world_gaze_deg")},
            "gate": [out["gate"]["admissible"], out["gate"]["reason"]], "executed": False}


# ------------------------------------------------------------------ visuals and manifest
def visualize(ctx: Ctx, vis: Path) -> dict:
    run = ctx.run
    need(run / "probe/decision.json", "probe")
    d = read_json(run / "probe/decision.json")
    if d["case"] == "B":
        need(run / "post/post-action-probe.json", "post-probe")
    import ns1b_visuals as V
    man = V.visualize(run, vis)
    write_manifest(run)
    return {k: v["sha256"] for k, v in man["figures"].items()}


def write_manifest(run: Path) -> dict:
    files = sorted(str(p.relative_to(run)) for p in run.rglob("*") if p.is_file()
                   and p.name not in ("manifest.json", "check-summary.json", "process-log.jsonl"))
    m = {"schema": "NS1b-manifest-v1", "experiment": SP.EXPERIMENT, "contract": SP.CONTRACT, "code": code_state(),
         "base_commit": SP.BASE_COMMIT, "truth": TRUTH_CLASSES, "files": {f: sha256(run / f) for f in files}}
    write_json(run / "manifest.json", m)
    return m


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=SP.COMMANDS)
    ap.add_argument("--run", type=Path, default=SP.RUN_DEFAULT)
    ap.add_argument("--visuals", type=Path, default=None)
    ap.add_argument("--dev", action="store_true", help="scratch development run only (never the canonical RUN)")
    ap.add_argument("--dev-target", type=int, default=None, help="select --dev only: a NON-candidate rehearsal entity")
    ap.add_argument("--rehearsal-spp", type=int, default=None, help="acquire --dev only: the factory-startup rehearsal")
    a = ap.parse_args(argv)
    ctx = Ctx(a.run, a.dev, a.dev_target if a.command == "select" else None)
    if a.rehearsal_spp is not None and (a.command != "acquire" or not a.dev):
        raise SystemExit(f"{PREFIX} --rehearsal-spp is an `acquire --dev` option only")
    if a.dev_target is not None and (a.command != "select" or not a.dev):
        raise SystemExit(f"{PREFIX} --dev-target is a `select --dev` option only")
    t0 = time.time()
    fns = {"source": source, "synthetic": synthetic, "select": select, "chart": chart, "covariance": covariance,
           "context": context, "probe": probe, "preflight": preflight,
           "acquire": lambda c: acquire(c, a.rehearsal_spp), "freeze-observation": freeze_observation,
           "perfect-correspondence": perfect_correspondence, "freeze-correspondence": freeze_correspondence,
           "spherical-geometry": spherical_geometry, "freeze-geometry": freeze_geometry,
           "local-oracle-segmentation": local_oracle_segmentation, "fuse": fuse, "post-probe": post_probe,
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
    print(f"{PREFIX} {a.command} ok " + json.dumps(out, sort_keys=True, default=str)[:800], flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
