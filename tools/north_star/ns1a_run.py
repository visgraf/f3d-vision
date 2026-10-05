"""North Star-1a: RGB bootstrap -> perfect local measurement -> persistent entity seeds (run order and truth boundary).

Contract: docs/north-star/ns1a-perfect-bootstrap-round-contract.md.

    .venv/bin/python tools/north_star/ns1a_run.py source                        --run RUN
    .venv/bin/python tools/north_star/ns1a_run.py synthetic                     --run RUN
    .venv/bin/python tools/north_star/ns1a_run.py preflight                     --run RUN   # Blender, NO render
    .venv/bin/python tools/north_star/ns1a_run.py acquire                       --run RUN   # Blender, the one render
    .venv/bin/python tools/north_star/ns1a_run.py freeze-observations           --run RUN
    .venv/bin/python tools/north_star/ns1a_run.py perfect-correspondence        --run RUN
    .venv/bin/python tools/north_star/ns1a_run.py freeze-correspondence         --run RUN
    .venv/bin/python tools/north_star/ns1a_run.py spherical-geometry            --run RUN
    .venv/bin/python tools/north_star/ns1a_run.py freeze-geometry               --run RUN
    .venv/bin/python tools/north_star/ns1a_run.py local-oracle-segmentation     --run RUN
    .venv/bin/python tools/north_star/ns1a_run.py persistent-seed-construction  --run RUN
    .venv/bin/python tools/north_star/ns1a_run.py freeze-seed-set               --run RUN
    .venv/bin/python tools/north_star/ns1a_run.py evaluate                      --run RUN
    .venv/bin/python tools/north_star/ns1a_run.py visualize                     --run RUN --visuals VIS

Every canonical stage runs once, from a clean pushed commit, under the accepted ``nb1a_guard.OpenGuard`` allowlist.
Before ``freeze-seed-set`` no stage opens the instance catalog, the Controller-01 seeds, Breadth-1 or any object name.
``--dev`` runs a stage on a scratch development run (never the canonical RUN) from a dirty tree; ``acquire --dev
--rehearsal-spp N`` renders the synthetic factory-startup rehearsal instead of Classroom.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
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

import ns1a_core as CORE  # noqa: E402
import ns1a_spec as SP  # noqa: E402
from nb1a_guard import OpenGuard  # noqa: E402  (accepted, read-only)

PREFIX = "[ns1a]"
TRUTH_CLASSES = {
    "ORACLE INPUT": "the coarse 360 RGB proxy and the rendered Classroom observations; the ORACLE AID (Position, "
                    "Object Index) used by the perfect correspondence and the local segmentation aid",
    "DERIVED": "the truth-stripped correspondence products, the spherical geometry, the local identity attachment, the "
               "persistent entity maps and the seed-set document",
    "REFERENCE / EVALUATION": "the sealed instance catalog, the accepted Controller-01 catalog and seeds, Breadth-1 and "
                              "the AB1b product, opened only after the seed freeze",
}


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
    """Read only the named members of an npz (the access is recorded by the caller)."""
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
    def __init__(self, run: Path, dev: bool) -> None:
        self.run, self.dev = run.resolve(), dev
        if dev and self.run == SP.RUN_DEFAULT.resolve():
            raise SystemExit(f"{PREFIX} STOP --dev never runs on the canonical RUN")

    def p(self, rel: str) -> Path:
        return self.run / rel


def log_process(ctx: Ctx, command: str, t0: float, status: str, extra: dict | None = None) -> None:
    ctx.run.mkdir(parents=True, exist_ok=True)
    entry = {"command": command, "argv": sys.argv, "executable": sys.executable, "code": code_state(),
             "dev": ctx.dev, "finished_utc": utc(), "seconds": round(time.time() - t0, 3), "status": status,
             **(extra or {})}
    with open(ctx.run / "process-log.jsonl", "a") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")


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


def guard_record(g: OpenGuard, extra: dict | None = None) -> dict:
    rec = g.record()
    rec["modules_loaded"] = {m: m in sys.modules for m in ("cv2", "fsg_stereo", "ab1a_stereo", "ab1d_match",
                                                           "ab1d3_sgbm", "ab1b_oracle", "integrated", "controller01",
                                                           "controller02", "fsg6f_public")}
    rec["truth_firewall_violations"] = len(rec["violations"])
    rec["forbidden_before_freeze_reads"] = sorted({e["path"] for e in rec["events"] if e.get("event") == "open"
                                                   and any(t in e["path"] for t in SP.FORBIDDEN_BEFORE_FREEZE)})
    rec.update(extra or {})
    return rec


def verify_record_hashes(run: Path, freeze_rel: str) -> dict:
    fz = read_json(run / freeze_rel)
    bad = {f: h for f, h in fz["files"].items() if sha256(run / f) != h}
    if bad:
        raise SystemExit(f"{PREFIX} STOP files changed after {freeze_rel}: {sorted(bad)[:5]}")
    return fz


# ------------------------------------------------------------------ source
def accepted_constants() -> dict:
    """The accepted persistent-map constants, read from the accepted sources (a mismatch is a STOP)."""
    from fov3d.experiments.classroom_oracle import config as public
    from fov3d.reconstruction import association, surface_map
    src = (REPO / "tools/fsg3_surface_map.py").read_text()
    lit = re.findall(r"len\(q\.xyz_h\) < (\d+)", src)
    got = {"MIN_INITIAL_TARGET_POINTS": int(public.MIN_INITIAL_TARGET_POINTS), "FUSION": dict(public.FUSION),
           "SURFACE_ASSOCIATION_RADIUS_M": float(association.SURFACE_ASSOCIATION_RADIUS_M),
           "fsg3_surface_map_point_literals": [int(x) for x in lit],
           "surface_map_legacy_module": surface_map.__legacy_module__}
    want = {"MIN_INITIAL_TARGET_POINTS": SP.MIN_INITIAL_TARGET_POINTS,
            "FUSION": {"association_radius_m": SP.ASSOCIATION_RADIUS_M, "hash_cell_m": SP.HASH_CELL_M},
            "SURFACE_ASSOCIATION_RADIUS_M": SP.ASSOCIATION_RADIUS_M,
            "fsg3_surface_map_point_literals": [SP.MIN_INITIAL_TARGET_POINTS] * 2,
            "surface_map_legacy_module": "tools.fsg3_surface_map"}
    if got != want:
        raise SystemExit(f"{PREFIX} STOP the accepted persistent-map constants differ: {got} != {want}")
    return got


def source(ctx: Ctx) -> dict:
    run = ctx.run
    once(run / "source/source-manifest.json", "the source record")
    cs = require_committed(ctx, "source")
    origin = git("remote", "get-url", "origin")
    anc = {}
    for name, sha in (("base", SP.BASE_COMMIT), ("ab1d3_acceptance", SP.AB1D3_ACCEPTANCE),
                      ("contract", SP.CONTRACT_COMMIT)):
        anc[name] = subprocess.run(["git", "merge-base", "--is-ancestor", sha, "HEAD"], cwd=REPO).returncode == 0
    contract_unchanged = subprocess.run(["git", "diff", "--quiet", SP.CONTRACT_COMMIT, "--", SP.CONTRACT],
                                        cwd=REPO).returncode == 0
    if SP.CANONICAL_REMOTE not in origin or not all(anc.values()) or not contract_unchanged:
        raise SystemExit(f"{PREFIX} STOP provenance: origin {origin}; ancestors {anc}; contract unchanged "
                         f"{contract_unchanged}")
    import fsg_geometry  # noqa: F401  (imports resolved before the guard)
    consts = accepted_constants()
    reads = [SP.NB1C_FREEZE[0], SP.NB1C_CANDIDATES[0], SP.NB1C_MANIFEST[0], SP.HEAD_POSE_SOURCE[0]]
    g = OpenGuard("ns1a-source", reads, [run / "source", run / "plan"])
    try:
        with g:
            pins = {p: sha256(REPO / p) for p in SP.SOURCE_PINS}
            bad = {p: h for p, h in pins.items() if h != SP.SOURCE_PINS[p]}
            if bad:
                raise SystemExit(f"{PREFIX} STOP accepted sources changed: {bad}")
            nb1c = {}
            for name, (path, want) in (("freeze", SP.NB1C_FREEZE), ("candidates", SP.NB1C_CANDIDATES),
                                       ("manifest", SP.NB1C_MANIFEST)):
                h = sha256(path)
                if h != want:
                    raise SystemExit(f"{PREFIX} STOP NB1c {name} changed: {h} != {want}")
                nb1c[name] = {"path": str(path), "sha256": h}
            man = read_json(SP.NB1C_MANIFEST[0])["files"]
            if (man.get("selection/rgb-gaze-freeze.json") != SP.NB1C_FREEZE[1]
                    or man.get("selection/candidate-gazes.json") != SP.NB1C_CANDIDATES[1]):
                raise SystemExit(f"{PREFIX} STOP the NB1c manifest does not list the pinned freeze")
            gazes = CORE.parse_gaze_list(read_json(SP.NB1C_FREEZE[0]), read_json(SP.NB1C_CANDIDATES[0]))
            hp = SP.HEAD_POSE_SOURCE[0]
            if sha256(hp) != SP.HEAD_POSE_SOURCE[1]:
                raise SystemExit(f"{PREFIX} STOP the head-pose source changed")
            head_b = Path(hp).read_bytes()
            head = json.loads(head_b)
            plans = {}
            for gz in gazes:
                c = CORE.planned_calibration(gz["yaw_deg"], gz["pitch_deg"], head["head_R_wh"],
                                             head["head_origin_w_m"])
                b = CORE.calibration_bytes(c)
                out = run / "plan" / SP.rank_dir(gz["rank"])
                out.mkdir(parents=True, exist_ok=True)
                (out / "planned-calibration.json").write_bytes(b)
                plans[gz["rank"]] = hashlib.sha256(b).hexdigest()
                if gz["rank"] == 1 and b != head_b:
                    raise SystemExit(f"{PREFIX} STOP the rank-1 planned calibration is not byte-identical to AB1a")
            write_json(run / "source/nb1c-gaze-list.json", {
                "schema": "NS1a-gaze-list-v1", "truth": SP.TRUTH_DERIVED, "source": nb1c,
                "statement": "the six frozen NB1c RGB gazes, in frozen order; the ONLY action source; no reselection, "
                             "filtering or replacement", "grid_convention": SP.GRID_CONVENTION, "gazes": gazes})
            summary = {"schema": "NS1a-source-v1", "experiment": SP.EXPERIMENT, "code": cs, "origin": origin,
                       "ancestors": anc, "contract": SP.CONTRACT, "contract_commit": SP.CONTRACT_COMMIT,
                       "contract_unchanged": contract_unchanged, "base_commit": SP.BASE_COMMIT,
                       "source_pins": pins, "accepted_constants": consts, "nb1c": nb1c,
                       "head_pose_source": {"path": str(hp), "sha256": SP.HEAD_POSE_SOURCE[1],
                                            "head_R_wh": head["head_R_wh"], "head_origin_w_m": head["head_origin_w_m"],
                                            "statement": "the accepted AB1a calibration; the Controller-01 seeds file "
                                                         "is NOT opened"},
                       "planned_calibration_sha256": {str(k): v for k, v in plans.items()},
                       "rank1_planned_byte_identical_to_ab1a": plans[1] == SP.HEAD_POSE_SOURCE[1]}
            write_json(run / "source/source-manifest.json", summary)
    finally:
        write_json(run / "source/source-opened-files.json", guard_record(g))
    return summary


# ------------------------------------------------------------------ synthetic known answers
def synthetic(ctx: Ctx) -> dict:
    run = ctx.run
    need(run / "source/source-manifest.json", "source")
    once(run / "synthetic/synthetic-report.json", "the synthetic known answers")
    require_committed(ctx, "synthetic")
    import ns1a_synthetic as SY
    rep = SY.run_all(run / "synthetic")
    write_json(run / "synthetic/synthetic-report.json", rep)
    if rep["failed"]:
        raise SystemExit(f"{PREFIX} STOP synthetic known answers failed: {rep['failed']}")
    return rep


# ------------------------------------------------------------------ Blender stages
def blender(ctx: Ctx, args: list[str], log: Path, factory: bool = False) -> None:
    log.parent.mkdir(parents=True, exist_ok=True)
    cmd = [SP.BLENDER, "-b"] + (["--factory-startup"] if factory else [str(REPO / SP.BLEND)])
    cmd += ["--python-exit-code", "1", "-P", str(HERE / "ns1a_render.py"), "--"] + args
    with open(log, "w") as f:
        p = subprocess.run(cmd, cwd=REPO, stdout=f, stderr=subprocess.STDOUT)
    text = log.read_text(errors="replace")
    if p.returncode != 0 or "[ns1a-render] COMPLETE" not in text or "[ns1a-render] FAILED" in text:
        raise SystemExit(f"{PREFIX} STOP Blender failed (exit {p.returncode}); see {log}")


def preflight(ctx: Ctx) -> dict:
    run = ctx.run
    rep = read_json(run / "synthetic/synthetic-report.json") if (run / "synthetic/synthetic-report.json").exists() else {}
    if rep.get("failed") != [] or not rep.get("passed"):
        raise SystemExit(f"{PREFIX} STOP the synthetic known answers must pass first")
    once(run / "preflight/preflight.json", "the Classroom preflight")
    require_committed(ctx, "preflight")
    if sha256(REPO / SP.BLEND) != SP.BLEND_SHA256:
        raise SystemExit(f"{PREFIX} STOP the Classroom blend changed")
    blender(ctx, ["--mode", "preflight", "--run", str(run)], run / "preflight/blender.log")
    return read_json(run / "preflight/preflight.json")


def acquire(ctx: Ctx, rehearsal_spp: int | None) -> dict:
    run = ctx.run
    if rehearsal_spp is None:
        need(run / "preflight/preflight.json", "preflight")
        if read_json(run / "preflight/preflight.json").get("rendered") is not False:
            raise SystemExit(f"{PREFIX} STOP the preflight record is not a no-render record")
    elif not ctx.dev:
        raise SystemExit(f"{PREFIX} STOP the rehearsal acquisition is a --dev command")
    once(run / "observations", "the six-gaze acquisition (never re-rendered)")
    require_committed(ctx, "acquire")
    if rehearsal_spp is None:
        if sha256(REPO / SP.BLEND) != SP.BLEND_SHA256:
            raise SystemExit(f"{PREFIX} STOP the Classroom blend changed")
        blender(ctx, ["--mode", "canonical", "--run", str(run)], run / "acquisition-blender.log")
    else:
        blender(ctx, ["--mode", "rehearsal", "--run", str(run), "--spp", str(int(rehearsal_spp))],
                run / "acquisition-blender.log", factory=True)
    ar = read_json(run / SP.ACQ_RUN_REL)
    if ar["ranks_in_order"] != list(SP.RANKS):
        raise SystemExit(f"{PREFIX} STOP the acquisition order {ar['ranks_in_order']} is not the frozen order")
    for r in SP.RANKS:
        for rel in [SP.acq_rel(r, n) for n in SP.OBS_ACQ_FILES] + [SP.aid_rel(r, n) for n in SP.OBS_AID_FILES]:
            need(run / rel, rel)
    return {"ranks": ar["ranks_in_order"], "budget": ar["budget"], "spp": ar["spp"]}


# ------------------------------------------------------------------ freeze-observations
def observation_files() -> list[str]:
    out = [SP.ACQ_RUN_REL]
    for r in SP.RANKS:
        out += [SP.acq_rel(r, n) for n in SP.OBS_ACQ_FILES] + [SP.aid_rel(r, n) for n in SP.OBS_AID_FILES]
    return out


def freeze_observations(ctx: Ctx) -> dict:
    run = ctx.run
    need(run / SP.ACQ_RUN_REL, "acquire")
    once(run / "freeze/observation-freeze.json", "the observation freeze")
    cs = require_committed(ctx, "freeze-observations")
    files = observation_files()
    plans = [run / "plan" / SP.rank_dir(r) / "planned-calibration.json" for r in SP.RANKS]
    g = OpenGuard("ns1a-freeze-observations", [run / f for f in files] + plans, [run / "freeze"])
    try:
        with g:
            hashes = {f: sha256(run / f) for f in files}
            ar = read_json(run / SP.ACQ_RUN_REL)
            problems = []
            for pr in ar["per_rank"]:
                r = pr["rank"]
                for key, rel in (("calibration_sha256", SP.acq_rel(r, "calibration.json")),
                                 ("rgb_observation_sha256", SP.acq_rel(r, "rgb-observation.npz")),
                                 ("reference_observation_sha256", SP.aid_rel(r, "reference-observation.npz"))):
                    if pr[key] != hashes[rel]:
                        problems.append(f"rank {r} {key}")
                rec = read_json(run / SP.acq_rel(r, "acquisition.json"))
                plan_b = (run / "plan" / SP.rank_dir(r) / "planned-calibration.json").read_bytes()
                if (run / SP.acq_rel(r, "calibration.json")).read_bytes() != plan_b:
                    problems.append(f"rank {r} calibration bytes != plan")
                want_spp = ar["spp"]
                if (rec["spp"] != want_spp or rec["render_seeds_lr"] != SP.SEEDS or rec["device"] != SP.DEVICE
                        or rec["nb1c_rank"] != r or rec["settings"]["samples"] != want_spp
                        or list(rec["gaze_yaw_pitch_deg"]) != [SP.GAZES[r - 1][3], SP.GAZES[r - 1][4]]):
                    problems.append(f"rank {r} acquisition record")
                if not ctx.dev and (want_spp != SP.SPP or pr["exr_samples_lr"] != {"L": str(SP.SPP), "R": str(SP.SPP)}):
                    problems.append(f"rank {r} spp / EXR samples")
                with np.load(run / SP.acq_rel(r, "rgb-observation.npz")) as z:
                    if sorted(z.files) != list(SP.RGB_KEYS):
                        problems.append(f"rank {r} rgb keys {z.files}")
                with np.load(run / SP.aid_rel(r, "reference-observation.npz")) as z:
                    if sorted(z.files) != sorted(SP.REFERENCE_KEYS):
                        problems.append(f"rank {r} reference keys {z.files}")
            if problems:
                raise SystemExit(f"{PREFIX} STOP observation problems: {problems}")
            fz = {"schema": "NS1a-observation-freeze-v1", "truth": SP.TRUTH_ORACLE, "frozen_utc": utc(), "code": cs,
                  "statement": "the six binocular observations, once each; never re-rendered. The sealed catalog is "
                               "NOT opened: its Blender-recorded seal is carried", "spp": ar["spp"],
                  "catalog_seal": ar["catalog_seal"], "files": hashes}
            write_json(run / "freeze/observation-freeze.json", fz)
    finally:
        write_json(run / "freeze/observation-freeze-opened-files.json", guard_record(g))
    return {"files": len(hashes), "spp": ar["spp"]}


# ------------------------------------------------------------------ the stage allowlists (used by the stages and tests)
def oracle_reads(run: Path, r: int) -> list[Path]:
    return [run / SP.acq_rel(r, "calibration.json"), run / SP.aid_rel(r, "reference-observation.npz"),
            run / "freeze/observation-freeze.json"]


def geometry_reads(run: Path, r: int) -> list[Path]:
    return [run / SP.acq_rel(r, "calibration.json"), run / f"correspondence/{SP.rank_dir(r)}/oracle-correspondences.npz"]


def segmentation_reads(run: Path) -> list[Path]:
    reads = [run / "freeze/geometry-freeze.json"] + [run / f for r in SP.RANKS for f in geom_files(r)]
    reads += [run / f"correspondence/{SP.rank_dir(r)}/oracle-correspondences.npz" for r in SP.RANKS]
    return reads + [run / SP.aid_rel(r, "reference-observation.npz") for r in SP.RANKS]


def seed_reads(run: Path) -> list[Path]:
    reads = [run / "freeze/geometry-freeze.json"] + [run / f for r in SP.RANKS for f in geom_files(r)]
    reads += [run / f for r in SP.RANKS for f in corr_files(r) + seg_files(r)]
    return reads + [run / SP.acq_rel(r, "rgb-observation.npz") for r in SP.RANKS] + [
        run / "segmentation/segmentation-opened-files.json"]


def evaluation_reads(run: Path, frozen: list[str]) -> list[Path]:
    reads = [run / "freeze/seed-set-freeze.json", run / "freeze/observation-freeze.json", run / SP.CATALOG_REL]
    reads += [run / f for f in frozen]
    reads += [run / SP.acq_rel(r, "calibration.json") for r in SP.RANKS]
    reads += [run / SP.aid_rel(r, "reference-observation.npz") for r in SP.RANKS]
    return reads + [SP.ACCEPTED_CATALOG[0], SP.C01_SEEDS[0], SP.BREADTH1_OBJECTS[0], SP.AB1B_PRODUCT[0]]


# ------------------------------------------------------------------ perfect correspondence (ORACLE AID)
def perfect_correspondence(ctx: Ctx) -> dict:
    run = ctx.run
    need(run / "freeze/observation-freeze.json", "freeze-observations")
    once(run / "correspondence", "the perfect correspondence")
    require_committed(ctx, "perfect-correspondence")
    import ab1b_oracle as O   # accepted AB1b oracle, read-only (imported before any guard)
    import fsg_geometry  # noqa: F401
    out = {}
    for r in SP.RANKS:
        cal, ref = run / SP.acq_rel(r, "calibration.json"), run / SP.aid_rel(r, "reference-observation.npz")
        odir = run / "correspondence" / SP.rank_dir(r)
        odir.mkdir(parents=True, exist_ok=True)
        g = OpenGuard(f"ns1a-oracle-{SP.rank_dir(r)}", oracle_reads(run, r), [odir])
        try:
            with g:
                fz = read_json(run / "freeze/observation-freeze.json")
                inputs = {}
                for name, path, rel in (("calibration", cal, SP.acq_rel(r, "calibration.json")),
                                        ("reference_observation", ref, SP.aid_rel(r, "reference-observation.npz"))):
                    h = sha256(path)
                    if h != fz["files"][rel]:
                        raise SystemExit(f"{PREFIX} STOP rank {r} {name} changed after the observation freeze")
                    inputs[name] = {"path": str(path), "sha256": h}
                c = read_json(cal)
                refd = O.load_reference(ref)
                product, summ = O.compute_oracle(c, refd)
                cls = CORE.core_class_map(c, refd)
                corr = np.flatnonzero(cls.ravel() == SP.CLASS_CORRESPONDENCE)
                want = product["left_core_row"].astype(np.int64) * SP.CORE_SIZE + product["left_core_col"]
                if not np.array_equal(corr, want):
                    raise SystemExit(f"{PREFIX} STOP rank {r}: the class map disagrees with the accepted product")
                np.savez_compressed(odir / "oracle-correspondences.npz", **product)
                np.savez_compressed(odir / "core-class-map.npz", core_class=cls)
                counts = {SP.CLASS_NAMES[k]: int((cls == k).sum()) for k in sorted(SP.CLASS_NAMES)}
                summary = {"schema": "NS1a-oracle-summary-v1", "truth": SP.TRUTH_DERIVED, "rank": r,
                           "label": SP.LABEL_ORACLE_CORR,
                           "statement": "PERFECT / ORACLE CORRESPONDENCE (accepted AB1b compute_oracle, read-only): "
                                        "Position and Object Index were used here, and only here, to choose and "
                                        "project the matches; the product holds core row / col and continuous "
                                        "uv_L / uv_R only",
                           "oracle": O.SP.ORACLE, "oracle_config_sha256": O.SP.config_sha256(O.SP.ORACLE),
                           "inputs": inputs, "product_keys": sorted(product), "core_class_counts": counts,
                           "instance_0": {"label": SP.UNASSIGNED,
                                          "finite_left_hits": int(summ["attrition"][1]["remaining"]),
                                          "positive_id_hits": int(summ["attrition"][2]["remaining"]),
                                          "id_0_hits": int(summ["excluded"]["hit_with_instance_0"])},
                           **summ}
                write_json(odir / "oracle-summary.json", summary)
                out[r] = summary["correspondences"]
        finally:
            write_json(odir / "correspondence-opened-files.json", guard_record(g))
    return out


def corr_files(r: int) -> list[str]:
    d = f"correspondence/{SP.rank_dir(r)}"
    return [f"{d}/oracle-correspondences.npz", f"{d}/oracle-summary.json", f"{d}/core-class-map.npz",
            f"{d}/correspondence-opened-files.json"]


def freeze_correspondence(ctx: Ctx) -> dict:
    run = ctx.run
    for r in SP.RANKS:
        need(run / f"correspondence/{SP.rank_dir(r)}/oracle-correspondences.npz", "perfect-correspondence")
    once(run / "freeze/correspondence-freeze.json", "the correspondence freeze")
    cs = require_committed(ctx, "freeze-correspondence")
    files = [f for r in SP.RANKS for f in corr_files(r)]
    import ab1b_geometry as BG
    g = OpenGuard("ns1a-freeze-correspondence", [run / f for f in files], [run / "freeze"])
    try:
        with g:
            for r in SP.RANKS:
                rec = read_json(run / f"correspondence/{SP.rank_dir(r)}/correspondence-opened-files.json")
                want = {str((run / SP.acq_rel(r, "calibration.json")).resolve()),
                        str((run / SP.aid_rel(r, "reference-observation.npz")).resolve()),
                        str((run / "freeze/observation-freeze.json").resolve())}
                if (rec["violations"] or set(rec["data_reads"]) != want or rec["modules_loaded"]["cv2"]
                        or rec["modules_loaded"]["fsg_stereo"] or rec["forbidden_before_freeze_reads"]):
                    raise SystemExit(f"{PREFIX} STOP rank {r}: the oracle guard record is not clean")
                BG.load_product(run / f"correspondence/{SP.rank_dir(r)}/oracle-correspondences.npz")
            fz = {"schema": "NS1a-correspondence-freeze-v1", "truth": SP.TRUTH_DERIVED, "frozen_utc": utc(),
                  "code": cs, "statement": "the six truth-stripped perfect-correspondence products, frozen before the "
                                           "spherical geometry", "files": {f: sha256(run / f) for f in files}}
            write_json(run / "freeze/correspondence-freeze.json", fz)
    finally:
        write_json(run / "freeze/correspondence-freeze-opened-files.json", guard_record(g))
    return {"files": len(files)}


# ------------------------------------------------------------------ truth-free spherical geometry
def truth_reads(events: list[dict]) -> dict:
    paths = [e["path"] for e in events if e.get("event") == "open"]
    ref = [p for p in paths if p.endswith("reference-observation.npz") or p.endswith(".exr") or "/oracle_aid/" in p
           or "evaluation_only" in p]
    return {"position_reads": len(ref), "object_index_reads": len(ref),
            "catalog_reads": len([p for p in paths if "catalog" in p])}


def geometry_rank(run: Path, r: int, probe=None) -> dict:
    """The accepted AB1b geometry for one gaze, under a guard reading exactly calibration + the frozen product."""
    import ab1b_geometry as BG   # accepted AB1b geometry, read-only
    import fsg_geometry as FG
    cal, prod_p = geometry_reads(run, r)
    odir = run / "geometry" / SP.rank_dir(r)
    odir.mkdir(parents=True, exist_ok=True)
    g = OpenGuard(f"ns1a-geometry-{SP.rank_dir(r)}", [cal, prod_p], [odir])
    try:
        with g:
            if probe is not None:
                probe()
            inputs = {"calibration": {"path": str(cal), "sha256": sha256(cal)},
                      "correspondences": {"path": str(prod_p), "sha256": sha256(prod_p)}}
            c = read_json(cal)
            FG.validate_calibration(c)
            prod = BG.load_product(prod_p)
            rays = BG.left_core_rays(c)
            res = BG.compute_epipolar(c, prod)
            np.savez_compressed(odir / "left-core-rays.npz", **rays)
            np.savez_compressed(odir / "epipolar-result.npz", **res)
            summary = {"schema": "NS1a-geometry-summary-v1", "truth": SP.TRUTH_DERIVED, "rank": r,
                       "label": SP.LABEL_GEOMETRY,
                       "statement": "TRUTH-FREE SPHERICAL EPIPOLAR RECONSTRUCTION (accepted AB1b geometry): the "
                                    "calibration and the frozen truth-stripped product only; no Position, Object "
                                    "Index or truth XYZ; canonical fixed-head H0 frame",
                       "geometry": BG.SP.GEOMETRY, "geometry_config_sha256": BG.SP.config_sha256(BG.SP.GEOMETRY),
                       "inputs": inputs, "baseline_m": float(c["ipd_m"]), "focal_px": float(c["eyes"][0]["K"][0][0]),
                       **BG.summarize(c, rays, res)}
            write_json(odir / "geometry-summary.json", summary)
    finally:
        rec = guard_record(g)
        rec.update(truth_reads(rec["events"]))
        write_json(odir / "geometry-opened-files.json", rec)
    return summary


def spherical_geometry(ctx: Ctx) -> dict:
    run = ctx.run
    if not (run / "freeze/correspondence-freeze.json").exists():   # existence only (no read); hashes in freeze-geometry
        raise SystemExit(f"{PREFIX} STOP freeze-correspondence comes first")
    once(run / "geometry", "the spherical geometry")
    require_committed(ctx, "spherical-geometry")
    return {r: geometry_rank(run, r)["counts"]["triangulated_epipolar"] for r in SP.RANKS}


def geom_files(r: int) -> list[str]:
    d = f"geometry/{SP.rank_dir(r)}"
    return [f"{d}/left-core-rays.npz", f"{d}/epipolar-result.npz", f"{d}/geometry-summary.json",
            f"{d}/geometry-opened-files.json"]


def freeze_geometry(ctx: Ctx) -> dict:
    run = ctx.run
    for r in SP.RANKS:
        need(run / f"geometry/{SP.rank_dir(r)}/epipolar-result.npz", "spherical-geometry")
    once(run / "freeze/geometry-freeze.json", "the geometry freeze")
    cs = require_committed(ctx, "freeze-geometry")
    files = [f for r in SP.RANKS for f in geom_files(r)]
    cfz = run / "freeze/correspondence-freeze.json"
    g = OpenGuard("ns1a-freeze-geometry", [run / f for f in files] + [cfz] + [run / f for r in SP.RANKS
                                                                               for f in corr_files(r)], [run / "freeze"])
    try:
        with g:
            fzc = verify_record_hashes(run, "freeze/correspondence-freeze.json")
            for r in SP.RANKS:
                rec = read_json(run / f"geometry/{SP.rank_dir(r)}/geometry-opened-files.json")
                summ = read_json(run / f"geometry/{SP.rank_dir(r)}/geometry-summary.json")
                prod_rel = f"correspondence/{SP.rank_dir(r)}/oracle-correspondences.npz"
                want = {str((run / SP.acq_rel(r, "calibration.json")).resolve()), str((run / prod_rel).resolve())}
                if (rec["violations"] or set(rec["data_reads"]) != want or any(rec["modules_loaded"].values())
                        or rec["position_reads"] or rec["object_index_reads"] or rec["catalog_reads"]
                        or summ["inputs"]["correspondences"]["sha256"] != fzc["files"][prod_rel]):
                    raise SystemExit(f"{PREFIX} STOP rank {r}: the geometry guard record or input is not clean")
            fz = {"schema": "NS1a-geometry-freeze-v1", "truth": SP.TRUTH_DERIVED, "frozen_utc": utc(), "code": cs,
                  "statement": "the six truth-free spherical geometries, frozen before any identity is attached",
                  "correspondence_freeze_sha256": sha256(cfz), "files": {f: sha256(run / f) for f in files}}
            write_json(run / "freeze/geometry-freeze.json", fz)
    finally:
        write_json(run / "freeze/geometry-freeze-opened-files.json", guard_record(g))
    return {"files": len(files)}


# ------------------------------------------------------------------ the local oracle segmentation aid
def local_oracle_segmentation(ctx: Ctx, probe=None) -> dict:
    run = ctx.run
    need(run / "freeze/geometry-freeze.json", "freeze-geometry")
    once(run / "segmentation", "the local oracle segmentation")
    require_committed(ctx, "local-oracle-segmentation")
    odir = run / "segmentation"
    odir.mkdir(parents=True, exist_ok=True)
    g = OpenGuard("ns1a-segmentation", segmentation_reads(run), [odir])
    members, out = {}, {}
    try:
        with g:
            verify_record_hashes(run, "freeze/geometry-freeze.json")
            g.mark("geometry_freeze_verified")
            g.mark("identity_access_begins")
            if probe is not None:
                probe()
            for r in SP.RANKS:
                prod = load_npz(run / f"correspondence/{SP.rank_dir(r)}/oracle-correspondences.npz")
                res = read_members(run / f"geometry/{SP.rank_dir(r)}/epipolar-result.npz", ("valid_epi",))
                ref = read_members(run / SP.aid_rel(r, "reference-observation.npz"), SP.SEGMENTATION_MEMBERS)
                members[str(r)] = list(SP.SEGMENTATION_MEMBERS)
                ids = CORE.attach_identity(prod, res["valid_epi"], ref["instance_L"])
                rd = odir / SP.rank_dir(r)
                rd.mkdir(parents=True, exist_ok=True)
                np.savez_compressed(rd / "local-identity.npz", left_core_row=prod["left_core_row"],
                                    left_core_col=prod["left_core_col"], temporary_entity_id=ids,
                                    valid=np.asarray(res["valid_epi"], bool))
                summ = {"schema": "NS1a-identity-summary-v1", "truth": SP.TRUTH_DERIVED, "rank": r,
                        "label": SP.LABEL_SEGMENTATION,
                        "statement": "ORACLE SEGMENTATION AID: temporary_entity_id = the left raw-core Object Index "
                                     "at the exact uv_L centre of each valid correspondence; not natural identity; no "
                                     "catalog, no names", "reference_members_read": list(SP.SEGMENTATION_MEMBERS),
                        **CORE.identity_summary(ids)}
                write_json(rd / "identity-summary.json", summ)
                out[r] = len(summ["entities"])
    finally:
        write_json(odir / "segmentation-opened-files.json", guard_record(g, {"reference_members_read": members}))
    return out


def seg_files(r: int) -> list[str]:
    d = f"segmentation/{SP.rank_dir(r)}"
    return [f"{d}/local-identity.npz", f"{d}/identity-summary.json"]


# ------------------------------------------------------------------ persistent entity seed construction
def gaze_inputs(run: Path) -> list[dict]:
    gazes = []
    for r in SP.RANKS:
        prod = load_npz(run / f"correspondence/{SP.rank_dir(r)}/oracle-correspondences.npz")
        res = read_members(run / f"geometry/{SP.rank_dir(r)}/epipolar-result.npz", ("P_epi", "valid_epi"))
        idn = load_npz(run / f"segmentation/{SP.rank_dir(r)}/local-identity.npz")
        rgb_l = read_members(run / SP.acq_rel(r, "rgb-observation.npz"), ("rgb_L",))["rgb_L"]
        uv = prod["uv_L"].astype(np.int64)
        if not (np.array_equal(idn["left_core_row"], prod["left_core_row"])
                and np.array_equal(idn["valid"], res["valid_epi"])):
            raise SystemExit(f"{PREFIX} STOP rank {r}: identity, product and geometry are not aligned")
        gazes.append({"rank": r, "xyz": res["P_epi"], "valid": res["valid_epi"], "ids": idn["temporary_entity_id"],
                      "rgb": rgb_l[uv[:, 1], uv[:, 0]].astype(np.float64)})
    return gazes


def unassigned_record(run: Path) -> dict:
    out = {"label": SP.UNASSIGNED, "statement": "instance 0 is never an ordinary entity; reported, never hidden; no "
                                                "background model", "per_rank": {}}
    for r in SP.RANKS:
        s = read_json(run / f"correspondence/{SP.rank_dir(r)}/oracle-summary.json")
        out["per_rank"][str(r)] = {**s["instance_0"], "core_pixels": s["left_core_pixels"],
                                   "id_0_fraction_of_finite_hits": (s["instance_0"]["id_0_hits"]
                                                                    / max(1, s["instance_0"]["finite_left_hits"])),
                                   "core_class_counts": s["core_class_counts"]}
    return out


def save_maps(path: Path, maps: dict) -> None:
    flat = {}
    for k, a in sorted(maps.items()):
        for f, v in a.items():
            flat[f"e{int(k):05d}_{f}"] = v
    np.savez_compressed(path, **flat)


def load_maps(path: Path) -> dict:
    out: dict[int, dict] = {}
    for key, v in load_npz(path).items():
        e, f = key.split("_", 1)
        out.setdefault(int(e[1:]), {})[f] = v
    return out


def persistent_seed_construction(ctx: Ctx, probe=None) -> dict:
    run = ctx.run
    for r in SP.RANKS:
        need(run / f"segmentation/{SP.rank_dir(r)}/local-identity.npz", "local-oracle-segmentation")
    once(run / "seeds", "the persistent seed construction")
    require_committed(ctx, "persistent-seed-construction")
    from fov3d.reconstruction import surface_map as SM   # accepted persistent-map machinery
    consts = accepted_constants()                         # imports resolved before the guard
    odir = run / "seeds"
    odir.mkdir(parents=True)
    g = OpenGuard("ns1a-seeds", seed_reads(run), [odir])
    try:
        with g:
            if probe is not None:
                probe()
            verify_record_hashes(run, "freeze/geometry-freeze.json")
            gz = gaze_inputs(run)
            result = CORE.construct_seeds(gz, SM, SP.MIN_INITIAL_TARGET_POINTS, SP.ASSOCIATION_RADIUS_M,
                                          SP.HASH_CELL_M)
            doc = CORE.seed_set_document(gz, result, unassigned_record(run))
            doc["accepted_constants"] = consts
            save_maps(odir / "entity-maps.npz", result["maps"])
            for r, snap in result["snapshots"].items():
                save_maps(odir / f"snapshot-after-{SP.rank_dir(r)}.npz", snap)
            write_json(odir / "construction-history.json", {
                "schema": "NS1a-construction-history-v1", "truth": SP.TRUTH_DERIVED,
                "statement": "initialization / fusion in frozen gaze order; per-gaze local entity measurements",
                "history": result["history"],
                "per_gaze": {str(r): {str(k): v for k, v in d.items()} for r, d in result["per_gaze"].items()}})
            write_json(odir / "seed-set.json", doc)
    finally:
        write_json(odir / "seeds-opened-files.json", guard_record(g))
    return doc["counts"]


def seed_files() -> list[str]:
    return (["seeds/entity-maps.npz", "seeds/construction-history.json", "seeds/seed-set.json",
             "seeds/seeds-opened-files.json"] + [f"seeds/snapshot-after-{SP.rank_dir(r)}.npz" for r in SP.RANKS])


def freeze_seed_set(ctx: Ctx) -> dict:
    run = ctx.run
    need(run / "seeds/seed-set.json", "persistent-seed-construction")
    once(run / "freeze/seed-set-freeze.json", "the seed-set freeze")
    cs = require_committed(ctx, "freeze-seed-set")
    files = ([f for r in SP.RANKS for f in corr_files(r) + geom_files(r) + seg_files(r)]
             + ["segmentation/segmentation-opened-files.json"] + seed_files()
             + ["freeze/observation-freeze.json", "freeze/correspondence-freeze.json", "freeze/geometry-freeze.json"])
    g = OpenGuard("ns1a-freeze-seed-set", [run / f for f in files], [run / "freeze"])
    try:
        with g:
            seg = read_json(run / "segmentation/segmentation-opened-files.json")
            seeds = read_json(run / "seeds/seeds-opened-files.json")
            for name, rec in (("segmentation", seg), ("seeds", seeds)):
                if rec["violations"] or rec["forbidden_before_freeze_reads"] or rec["modules_loaded"]["cv2"]:
                    raise SystemExit(f"{PREFIX} STOP the {name} guard record is not clean")
            if any(v != list(SP.SEGMENTATION_MEMBERS) for v in seg["reference_members_read"].values()):
                raise SystemExit(f"{PREFIX} STOP the segmentation read more than {SP.SEGMENTATION_MEMBERS}")
            fz = {"schema": "NS1a-seed-set-freeze-v1", "truth": SP.TRUTH_DERIVED, "frozen_utc": utc(), "code": cs,
                  "statement": "the persistent entity seed set, frozen BEFORE the catalog, any object name, Breadth-1 "
                               "or the Controller-01 seeds are opened", "files": {f: sha256(run / f) for f in files}}
            write_json(run / "freeze/seed-set-freeze.json", fz)
    finally:
        write_json(run / "freeze/seed-set-freeze-opened-files.json", guard_record(g))
    return {"files": len(files)}


# ------------------------------------------------------------------ post-freeze descriptive evaluation
def quant(a) -> dict | None:
    a = np.asarray(a, np.float64)
    a = a[np.isfinite(a)]
    if not a.size:
        return None
    return {k: float(np.quantile(a, q)) for k, q in SP.QUANTILES.items()} | {"count": int(a.size)}


def catalog_map(d: dict) -> dict[int, str]:
    return {int(e["instance_id"]): str(e["object_name"]) for e in d["instances"]}


def oracle_consistency(run: Path, r: int) -> dict:
    """REFERENCE / EVALUATION: the frozen P_epi against the left Position at the exact uv_L pixel (head frame)."""
    import fsg_geometry as FG
    c = read_json(run / SP.acq_rel(r, "calibration.json"))
    prod = load_npz(run / f"correspondence/{SP.rank_dir(r)}/oracle-correspondences.npz")
    res = read_members(run / f"geometry/{SP.rank_dir(r)}/epipolar-result.npz", ("P_epi", "valid_epi", "kappa",
                                                                                "range_L"))
    pos = read_members(run / SP.aid_rel(r, "reference-observation.npz"), ("position_w_L",))["position_w_L"]
    uv = prod["uv_L"].astype(np.int64)
    p_h = FG.world_to_head(c, pos[uv[:, 1], uv[:, 0]].astype(np.float64))
    v = np.asarray(res["valid_epi"], bool)
    err = np.linalg.norm(res["P_epi"] - p_h, axis=-1)[v]
    return {"pairs": int(v.sum()), "error_m": quant(err), "kappa": quant(np.asarray(res["kappa"])[v]),
            "range_L_m": quant(np.asarray(res["range_L"])[v]),
            "within_1mm": float((err <= 1e-3).mean()) if err.size else None,
            "within_12mm": float((err <= 0.012).mean()) if err.size else None}


def ab1b_reproduction(run: Path) -> dict:
    """REFERENCE / EVALUATION: rank 1 (same calibration as AB1a) against the accepted AB1b oracle (256 spp)."""
    a = load_npz(SP.AB1B_PRODUCT[0])
    b = load_npz(run / "correspondence/rank-01/oracle-correspondences.npz")
    ka = a["left_core_row"].astype(np.int64) * SP.CORE_SIZE + a["left_core_col"]
    kb = b["left_core_row"].astype(np.int64) * SP.CORE_SIZE + b["left_core_col"]
    common, ia, ib = np.intersect1d(ka, kb, return_indices=True)
    d = np.linalg.norm(a["uv_R"][ia] - b["uv_R"][ib], axis=-1)
    return {"ab1b_pairs": int(ka.size), "ns1a_rank1_pairs": int(kb.size), "common": int(common.size),
            "only_ab1b": int(ka.size - common.size), "only_ns1a": int(kb.size - common.size),
            "uv_R_difference_px": quant(d),
            "statement": "descriptive: the same calibration and seeds; 256 spp (AB1a) vs 4096 spp (NS1a) truth passes"}


def evaluate(ctx: Ctx) -> dict:
    run = ctx.run
    need(run / "freeze/seed-set-freeze.json", "freeze-seed-set")
    once(run / "evaluation/evaluation.json", "the evaluation")
    cs = require_committed(ctx, "evaluate")
    import fsg_geometry  # noqa: F401  (imported before the guard)
    sfz = read_json(run / "freeze/seed-set-freeze.json")
    odir = run / "evaluation"
    odir.mkdir(parents=True, exist_ok=True)
    g = OpenGuard("ns1a-evaluate", evaluation_reads(run, list(sfz["files"])), [odir])
    try:
        with g:
            verify_record_hashes(run, "freeze/seed-set-freeze.json")
            g.mark("seed_freeze_verified")
            g.mark("reference_access_begins")
            seal = read_json(run / "freeze/observation-freeze.json")["catalog_seal"]
            if sha256(run / SP.CATALOG_REL) != seal["sha256"]:
                raise SystemExit(f"{PREFIX} STOP the sealed catalog does not match its Blender seal")
            for path, want in (SP.ACCEPTED_CATALOG, SP.C01_SEEDS, SP.BREADTH1_OBJECTS, SP.AB1B_PRODUCT):
                if sha256(path) != want:
                    raise SystemExit(f"{PREFIX} STOP pinned reference changed: {path}")
            cat = catalog_map(read_json(run / SP.CATALOG_REL))
            acc = catalog_map(read_json(SP.ACCEPTED_CATALOG[0]))
            b1 = read_json(SP.BREADTH1_OBJECTS[0])["objects"]
            visible = {int(o["instance_id"]) for o in b1 if o["status"] == "VISIBLE_AT_0P5_DEG"}
            loc25 = sorted(int(s["instance_id"]) for s in read_json(SP.C01_SEEDS[0])["instances"])
            b1_loc = sorted(int(o["instance_id"]) for o in b1 if o["in_accepted_localized_25"])
            doc = read_json(run / "seeds/seed-set.json")
            ents = doc["entities"]
            observed = [e["temporary_entity_id"] for e in ents]
            init = [e["temporary_entity_id"] for e in ents if e["initialized"]]
            table = [{"temporary_entity_id": e["temporary_entity_id"], "post_freeze_name": cat.get(e["temporary_entity_id"]),
                      "first_seen_rank": e["first_seen_rank"], "gaze_ranks_seen": e["gaze_ranks_seen"],
                      "initialized": e["initialized"], "initialized_at_rank": e["initialized_at_rank"],
                      "final_surfels": e["final_surfels"], "contributing_patches": e["contributing_patches"],
                      "total_raw_measured_points": e["total_raw_measured_points"],
                      "breadth1_visible": e["temporary_entity_id"] in visible,
                      "controller01_localized": e["temporary_entity_id"] in loc25} for e in ents]
            un = doc["unassigned_instance_0"]["per_rank"]
            hits = sum(v["finite_left_hits"] for v in un.values())
            zero = sum(v["id_0_hits"] for v in un.values())
            per_rank = {}
            for r in SP.RANKS:
                ids_here = sorted(int(k) for k in read_json(run / f"segmentation/{SP.rank_dir(r)}/identity-summary.json")["entities"])
                per_rank[str(r)] = {"positive_ids": ids_here, "names": [cat.get(k) for k in ids_here],
                                    "initialized_here": sorted(e["temporary_entity_id"] for e in ents
                                                               if e["initialized_at_rank"] == r),
                                    "instance_0": un[str(r)], "oracle_consistency": oracle_consistency(run, r)}
            ev = {"schema": "NS1a-evaluation-v1", "truth": SP.TRUTH_REFERENCE, "code": cs,
                  "statement": "post-freeze, descriptive only: the catalog, names, Breadth-1 and the Controller-01 "
                               "seeds were opened only after the seed freeze verified; nothing here changes a gaze, "
                               "an entity id, a map, an initialization, a fusion or the seed ordering",
                  "catalog": {"sealed_matches_seal": True, "instances": len(cat), "equal_to_accepted_controller01": cat == acc},
                  "counts": {"unique_positive_entities_observed": len(observed), "initialized": len(init),
                             "seen_but_not_initialized": len(observed) - len(init),
                             "gazes_with_an_initialized_entity": doc["counts"]["gazes_with_an_initialized_entity"]},
                  "first_encounter": {str(e["temporary_entity_id"]): e["first_seen_rank"] for e in ents},
                  "instance_0": {"finite_left_hits": hits, "id_0_hits": zero,
                                 "id_0_fraction_of_finite_hits": zero / max(1, hits),
                                 "per_rank_fraction": {k: v["id_0_fraction_of_finite_hits"] for k, v in un.items()}},
                  "breadth1": {"visible_catalog_entities": len(visible),
                               "observed_and_visible": sorted(set(observed) & visible),
                               "initialized_and_visible": sorted(set(init) & visible),
                               "touched_fraction_observed": len(set(observed) & visible) / len(visible),
                               "touched_fraction_initialized": len(set(init) & visible) / len(visible),
                               "observed_not_breadth1_visible": sorted(set(observed) - visible)},
                  "controller01": {"localized_25": loc25, "breadth1_flag_agrees": loc25 == b1_loc,
                                   "observed_and_localized": sorted(set(observed) & set(loc25)),
                                   "initialized_and_localized": sorted(set(init) & set(loc25)),
                                   "observed_not_localized": sorted(set(observed) - set(loc25))},
                  "entities": table, "per_rank": per_rank, "ab1b_rank1_reproduction": ab1b_reproduction(run)}
            verify_record_hashes(run, "freeze/seed-set-freeze.json")
            g.mark("seed_freeze_reverified")
            write_json(odir / "evaluation.json", ev)
    finally:
        write_json(odir / "evaluation-opened-files.json", guard_record(g))
    return ev["counts"]


def visualize(ctx: Ctx, vis: Path) -> dict:
    run = ctx.run
    need(run / "evaluation/evaluation.json", "evaluate")
    import ns1a_visuals as V
    man = V.visualize(run, vis)
    write_manifest(run)
    return {k: v["sha256"] for k, v in man["figures"].items()}


def write_manifest(run: Path) -> dict:
    files = sorted(str(p.relative_to(run)) for p in run.rglob("*") if p.is_file()
                   and p.name not in ("manifest.json", "check-summary.json", "process-log.jsonl"))
    m = {"schema": "NS1a-manifest-v1", "experiment": SP.EXPERIMENT, "contract": SP.CONTRACT, "code": code_state(),
         "base_commit": SP.BASE_COMMIT, "truth": TRUTH_CLASSES, "files": {f: sha256(run / f) for f in files}}
    write_json(run / "manifest.json", m)
    return m


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=SP.COMMANDS)
    ap.add_argument("--run", type=Path, default=SP.RUN_DEFAULT)
    ap.add_argument("--visuals", type=Path, default=None)
    ap.add_argument("--dev", action="store_true", help="scratch development run only (never the canonical RUN)")
    ap.add_argument("--rehearsal-spp", type=int, default=None, help="acquire --dev only: the factory-startup rehearsal")
    a = ap.parse_args(argv)
    ctx = Ctx(a.run, a.dev)
    if a.rehearsal_spp is not None and (a.command != "acquire" or not a.dev):
        raise SystemExit(f"{PREFIX} --rehearsal-spp is an `acquire --dev` option only")
    t0 = time.time()
    fns = {"source": source, "synthetic": synthetic, "preflight": preflight,
           "acquire": lambda c: acquire(c, a.rehearsal_spp), "freeze-observations": freeze_observations,
           "perfect-correspondence": perfect_correspondence, "freeze-correspondence": freeze_correspondence,
           "spherical-geometry": spherical_geometry, "freeze-geometry": freeze_geometry,
           "local-oracle-segmentation": local_oracle_segmentation,
           "persistent-seed-construction": persistent_seed_construction, "freeze-seed-set": freeze_seed_set,
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
    log_process(ctx, a.command, t0, "ok", {"result": out if a.command != "synthetic" else
                                           {"passed": out["passed"], "failed": out["failed"]}})
    print(f"{PREFIX} {a.command} ok " + json.dumps(out if a.command != "synthetic" else
                                                   {"passed": len(out["passed"]), "failed": out["failed"]},
                                                   sort_keys=True, default=str)[:600], flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
