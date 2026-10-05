"""Active Bootstrap-1d: safe-forward natural RGB correspondence (run order and truth boundary).

Contract: docs/active-bootstrap/ab1d-safe-forward-natural-correspondence-contract.md.

    .venv/bin/python tools/active_bootstrap/ab1d_run.py source                --run RUN
    .venv/bin/python tools/active_bootstrap/ab1d_run.py synthetic             --run RUN
    .venv/bin/python tools/active_bootstrap/ab1d_run.py match                 --run RUN
    .venv/bin/python tools/active_bootstrap/ab1d_run.py freeze-correspondence --run RUN
    .venv/bin/python tools/active_bootstrap/ab1d_run.py spherical             --run RUN
    .venv/bin/python tools/active_bootstrap/ab1d_run.py freeze-geometry       --run RUN
    .venv/bin/python tools/active_bootstrap/ab1d_run.py evaluate              --run RUN
    .venv/bin/python tools/active_bootstrap/ab1d_run.py visualize             --run RUN --visuals VIS

``match`` reads exactly the AB1c calibration and RGB observation of each gaze (allowlist guard) and writes the full-core
matcher record and the truth-stripped natural product, frozen by ``freeze-correspondence``; ``spherical`` (accepted AB1b
geometry) reads only the calibration and that product; ``freeze-geometry`` freezes it; only then ``evaluate`` opens the
AB1c perfect-correspondence benchmark and Position (REFERENCE / EVALUATION).  There is no Blender process and no render.
This module does not import the matcher at load time (so the geometry stage loads neither cv2 nor the matcher).
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

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _p in (HERE, HERE.parent, HERE.parent / "natural_bootstrap"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import ab1b_geometry as BG  # noqa: E402  (accepted spherical geometry, read-only)
import ab1d_spec as SP  # noqa: E402
import fsg_geometry as FG  # noqa: E402  (accepted, read-only)
from nb1a_guard import OpenGuard  # noqa: E402  (accepted, read-only)

PREFIX = "[ab1d]"
TRUTH_CLASSES = {"ORACLE INPUT": "the rendered AB1c RGB observations",
                 "DERIVED": "natural matcher records and products, spherical geometry, synthetic known answers",
                 "REFERENCE / EVALUATION": "the AB1c perfect correspondence (benchmark only), the AB1c perfect spherical "
                                           "reconstruction and Blender Position, opened only after the geometry freeze"}


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


def log_process(run: Path, command: str, t0: float, status: str, extra: dict | None = None) -> None:
    run.mkdir(parents=True, exist_ok=True)
    entry = {"command": command, "argv": sys.argv, "executable": sys.executable, "code": code_state(),
             "finished_utc": utc(), "seconds": round(time.time() - t0, 3), "status": status, **(extra or {})}
    with open(run / "process-log.jsonl", "a") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")


def require_committed(what: str) -> dict:
    cs = code_state()
    if cs["dirty"] or not cs["pushed"]:
        raise SystemExit(f"{PREFIX} STOP {what} runs only from a clean, pushed implementation commit: {cs}")
    return cs


def once(path: Path, what: str) -> None:
    if Path(path).exists():
        raise SystemExit(f"{PREFIX} STOP {what} exists ({path}); it is made once")


def need(path: Path, what: str) -> None:
    if not Path(path).is_file():
        raise SystemExit(f"{PREFIX} STOP {what} comes first ({path} missing)")


def verify_sources() -> None:
    bad = {p: sha256(REPO / p) for p, h in SP.SOURCE_PINS.items() if sha256(REPO / p) != h}
    if bad:
        raise SystemExit(f"{PREFIX} STOP accepted sources changed: {bad}")


def verify_observations() -> dict:
    """Hash the matcher-time inputs (calibration + RGB) of every gaze against the pins."""
    out = {}
    for g in SP.GAZES:
        for name, path in (("calibration", SP.calibration_path(g)), ("rgb", SP.rgb_path(g))):
            rel = SP.OBS_TMPL.format(g=g, name=path.name)
            h = sha256(path)
            if h != SP.OBS_PINS[rel]:
                raise SystemExit(f"{PREFIX} STOP {g} {name} changed: {h} != {SP.OBS_PINS[rel]}")
            out[rel] = h
    return out


def truth_reads(events: list[dict]) -> dict:
    """Reads the natural stages must never make, counted from every open event (allowed or refused)."""
    paths = [e["path"] for e in events if e.get("event") == "open"]
    root = str(SP.A1C_RUN.resolve())

    def under(p: str, sub: str) -> bool:
        return p.startswith(root + "/" + sub + "/")
    pos = [p for p in paths if p.endswith("reference-observation.npz") or p.endswith(".exr") or "/evaluation_only/" in p]
    ora = [p for p in paths if "oracle-correspondences" in p or under(p, "oracle")]
    ev = [p for p in paths if "evaluation-result" in p or "instance-catalog" in p
          or any(under(p, s) for s in ("evaluation", "planar", "comparison", "spherical", "freeze"))]
    return {"position_reads": len(pos), "object_index_reads": len(pos), "oracle_reads": len(ora),
            "evaluation_reads": len(ev)}


# ------------------------------------------------------------------ source (section 3)
def source(run: Path) -> dict:
    out = run / "source/source-manifest.json"
    once(out, "the source manifest")
    verify_sources()
    import ab1b_spec as BS
    import fsg_stereo as FS
    remote = git("remote", "get-url", "origin")
    man_path = SP.a1c(SP.A1C_MANIFEST[0])
    man = read_json(man_path)["files"]
    obs = verify_observations()
    acq = {}
    for g in SP.GAZES:
        a = read_json(SP.obs_path(g, "acquisition.json"))
        gt = SP.GAZE_TABLE[g]
        acq[g] = (a["rgb_observation_sha256"] == obs[SP.OBS_TMPL.format(g=g, name="rgb-observation.npz")]
                  and a["calibration_sha256"] == obs[SP.OBS_TMPL.format(g=g, name="calibration.json")]
                  and list(a["gaze_yaw_pitch_deg"]) == [gt["yaw_deg"], gt["pitch_deg"]])
    sel = read_json(SP.a1c("selection/selected-gazes.json"))["gazes"]
    sel_ok = [(s["row"], s["col"], s["yaw_deg"], s["pitch_deg"]) for s in sel] == [
        (SP.GAZE_TABLE[g]["row"], SP.GAZE_TABLE[g]["col"], SP.GAZE_TABLE[g]["yaw_deg"], SP.GAZE_TABLE[g]["pitch_deg"])
        for g in SP.GAZES]
    cal_ok = all(read_json(SP.calibration_path(g))["eyes"][0]["K"][0][0] == SP.FOCAL_PX
                 and read_json(SP.calibration_path(g))["ipd_m"] == SP.IPD_M for g in SP.GAZES)
    ident = {
        "canonical_remote": remote.rstrip("/").removesuffix(".git").endswith(SP.CANONICAL_REMOTE),
        "a1c_manifest": sha256(man_path) == SP.A1C_MANIFEST[1],
        "a1c_visuals_manifest": sha256(SP.A1C_VIS_MANIFEST[0]) == SP.A1C_VIS_MANIFEST[1],
        "observation_pins_in_a1c_manifest": all(man.get(k) == h for k, h in SP.OBS_PINS.items()),
        "observation_files": all(sha256(SP.a1c(k)) == h for k, h in SP.OBS_PINS.items()),
        "benchmark_pins_in_a1c_manifest": all(man.get(k) == h for k, h in SP.BENCH_PINS.items()),
        "acquisition_records": all(acq.values()),
        "selected_gazes": sel_ok,
        "calibrations": cal_ok,
        "fsg_constants": FS.MIN_LOCAL_STD_U8 == SP.MIN_LOCAL_STD_U8 and FS.BLOCK_SIZE == SP.PATCH,
        "ab1b_constants": BS.DEN_EPS == SP.DEN_EPS and tuple(BS.BASELINE_AXIS) == SP.BASELINE_AXIS
                          and BS.CORE_SIZE == SP.CORE_SIZE and BS.CORE_ORIGIN == SP.CORE_ORIGIN,
    }
    if not all(ident.values()):
        raise SystemExit(f"{PREFIX} STOP source identity: {ident}")
    rec = {"schema": "AB1d-source-manifest-v1", "truth": SP.TRUTH_DERIVED, "experiment": SP.EXPERIMENT,
           "statement": "pinned sources verified; the three AB1c observations are reused exactly (no render); the "
                        "benchmark files are verified here only through the AB1c manifest and are hashed again, then "
                        "opened, only after the geometry freeze",
           "remote": remote, "identity": ident, "a1c_run": str(SP.A1C_RUN),
           "a1c_manifest": {"path": str(man_path), "sha256": SP.A1C_MANIFEST[1]},
           "observations": SP.OBS_PINS, "benchmark_pins": SP.BENCH_PINS, "gazes": SP.GAZE_TABLE,
           "source_pins": SP.SOURCE_PINS, "matcher_config_sha256": SP.config_sha256(SP.MATCHER),
           "base_commit": SP.BASE_COMMIT, "contract_commit": SP.CONTRACT_COMMIT, "code": code_state(),
           "created_utc": utc()}
    write_json(out, rec)
    print(f"{PREFIX} source: {len(SP.SOURCE_PINS)} code pins, {len(SP.OBS_PINS)} AB1c observation pins, "
          f"{len(SP.BENCH_PINS)} benchmark pins (manifest only), canonical remote verified")
    return rec


# ------------------------------------------------------------------ synthetic (section 24)
def synthetic(run: Path) -> dict:
    import ab1d_synthetic as SY
    rep = SY.run_synthetic(run / "synthetic")
    rep["code"] = code_state()
    write_json(run / "synthetic/synthetic-report.json", rep)
    for x in rep["cases"]:
        print(f"{PREFIX} synthetic {'PASS' if x['passed'] else 'FAIL'} {x['case']:2d} {x['name']}")
    print(f"{PREFIX} {'AB1D_SYNTHETIC_PASS' if rep['passed'] else 'SYNTHETIC FAILED'} "
          f"{sum(x['passed'] for x in rep['cases'])}/{len(rep['cases'])} in {rep['seconds']} s")
    return rep


# ------------------------------------------------------------------ match (sections 5-14)
TRIPWIRES = ("StereoSGBM_create", "StereoBM_create", "stereoRectify", "initUndistortRectifyMap", "remap")


def run_match_gaze(calib_path: Path, rgb_path: Path, out_dir: Path, idx=None, probe=None) -> dict:
    """The frozen matcher under the allowlist guard: exactly the calibration and the RGB observation."""
    import ab1d_match as M
    out_dir.mkdir(parents=True, exist_ok=True)
    calls: dict[str, int] = {}
    cv2 = sys.modules.get("cv2")
    saved = {}
    if cv2 is not None:
        for name in TRIPWIRES:
            if hasattr(cv2, name):
                saved[name] = getattr(cv2, name)

                def trip(*a, _n=name, **k):
                    calls[_n] = calls.get(_n, 0) + 1
                    raise RuntimeError(f"AB1d tripwire: cv2.{_n} called")
                setattr(cv2, name, trip)
    g = OpenGuard("ab1d-match", [calib_path, rgb_path], [out_dir])
    summary = None
    try:
        with g:
            inputs = {"calibration": {"path": str(calib_path), "sha256": sha256(calib_path)},
                      "rgb_observation": {"path": str(rgb_path), "sha256": sha256(rgb_path)}}
            c = read_json(calib_path)
            FG.validate_calibration(c)
            obs = load_npz(rgb_path)
            M.validate_observation(obs, tuple(c["image_size_wh"]))
            t0 = time.perf_counter()
            ctx = M.Context(c, M.gray(obs["rgb_L"]), M.gray(obs["rgb_R"]))
            rec = M.match(ctx, idx)
            seconds = time.perf_counter() - t0
            if probe is not None:
                probe()
            prod = M.product(rec)
            np.savez_compressed(out_dir / "matcher-record.npz", **rec)
            np.savez_compressed(out_dir / "natural-correspondences.npz", **prod)
            summary = match_summary(rec, prod, inputs, seconds, ctx)
            write_json(out_dir / "match-summary.json", summary)
    finally:
        if cv2 is not None:
            for name, fn in saved.items():
                setattr(cv2, name, fn)
        rec_g = g.record()
        rec_g["modules_loaded"] = {m: m in sys.modules for m in ("torch", "tensorflow", "onnxruntime", "ab1c_planar",
                                                                 "ab1b_oracle", "ab1c_render", "bpy")}
        rec_g["cv2_tripwire_calls"] = calls
        rec_g.update(truth_reads(rec_g["events"]))
        rec_g["truth_firewall_violations"] = len(rec_g["violations"])
        write_json(out_dir / "match-opened-files.json", rec_g)
    return summary


def qd(a, mask=None) -> dict | None:
    a = np.asarray(a, np.float64)
    if mask is not None:
        a = a[np.asarray(mask, bool)]
    a = a[np.isfinite(a)].ravel()
    if a.size == 0:
        return None
    return {k: float(np.quantile(a, v)) for k, v in SP.QUANTILES.items()} | {"count": int(a.size)}


def match_summary(rec: dict, prod: dict, inputs: dict, seconds: float, ctx) -> dict:
    v = rec["valid_match"]
    reasons = {SP.REASONS[k]: int((rec["reason"] == k).sum()) for k in SP.REASONS}
    return {"schema": "AB1d-match-summary-v1", "truth": SP.TRUTH_DERIVED,
            "statement": "NATURAL CORRESPONDENCE: the frozen primitive matcher on the calibration and the RGB observation "
                         "only; no Position, Object Index, oracle, depth or truth; no SGBM, learned model or planar "
                         "rectification",
            "matcher": SP.MATCHER, "matcher_config_sha256": SP.config_sha256(SP.MATCHER), "inputs": inputs,
            "seconds": round(seconds, 3), "threads": SP.THREADS, "batch": SP.BATCH, "delta_rad": ctx.delta,
            "focal_px": ctx.cam_l.f,
            "counts": {"left_core": int(v.size), "left_textured": int(rec["valid_left_texture"].sum()),
                       "natural_valid": int(v.sum()), "product_pairs": int(prod["left_core_row"].size),
                       "reasons": reasons, "refined": int(rec["refined"].sum())},
            "candidates": {"admissible": qd(rec["candidate_count"]), "textured": qd(rec["textured_candidate_count"]),
                           "admissible_valid_only": qd(rec["candidate_count"], v)},
            "distributions": {"best_zncc": qd(rec["best_zncc"], v), "peak_margin": qd(rec["peak_margin"], v),
                              "peak_curvature": qd(rec["peak_curvature"], v),
                              "refinement_offset_samples": qd(rec["refinement_offset_samples"], v & rec["refined"]),
                              "left_patch_std_u8": qd(rec["left_patch_std_u8"]),
                              "peak_count": {str(n): int((rec["peak_count"][v] == n).sum()) for n in range(SP.TOP_K + 1)},
                              "single_peak": int((v & ~np.isfinite(rec["peak_margin"])).sum())}}


def match(run: Path) -> dict:
    once(run / "match" / SP.GAZES[0] / "matcher-record.npz", "the natural match")
    need(run / "source/source-manifest.json", "source")
    rep_path = run / "synthetic/synthetic-report.json"
    need(rep_path, "synthetic")
    rep, cs = read_json(rep_path), code_state()
    if not rep["passed"] or rep["code"]["commit"] != cs["commit"] or rep["code"]["dirty"]:
        raise SystemExit(f"{PREFIX} STOP match needs a passing synthetic report from this exact clean commit")
    verify_sources()
    verify_observations()
    out = {}
    for g in SP.GAZES:
        summ = run_match_gaze(SP.calibration_path(g), SP.rgb_path(g), run / "match" / g)
        rec = read_json(run / "match" / g / "match-opened-files.json")
        want = {str(SP.calibration_path(g).resolve()), str(SP.rgb_path(g).resolve())}
        bad = (rec["violations"] or set(rec["data_reads"]) != want or any(rec["modules_loaded"].values())
               or rec["cv2_tripwire_calls"] or any(rec[k] for k in ("position_reads", "object_index_reads",
                                                                    "oracle_reads", "evaluation_reads")))
        if bad:
            raise SystemExit(f"{PREFIX} STOP {g} match guard: reads {rec['data_reads']}; violations {rec['violations']}")
        k = summ["counts"]
        print(f"{PREFIX} match {g}: textured {k['left_textured']:,}, natural valid {k['natural_valid']:,} / "
              f"{k['left_core']:,}; candidates median {summ['candidates']['admissible']['median']:.0f}; "
              f"{summ['seconds']:.1f} s; truth reads 0")
        out[g] = summ
    return out


def corr_files(g: str) -> list[str]:
    return [f"match/{g}/{n}" for n in ("matcher-record.npz", "natural-correspondences.npz", "match-summary.json",
                                       "match-opened-files.json")]


def freeze_correspondence(run: Path) -> dict:
    path = run / "match/correspondence-freeze.json"
    once(path, "the natural correspondence freeze")
    files, inputs = {}, {}
    for g in SP.GAZES:
        for n in corr_files(g):
            need(run / n, n)
        rec = read_json(run / "match" / g / "match-opened-files.json")
        want = {str(SP.calibration_path(g).resolve()), str(SP.rgb_path(g).resolve())}
        if rec["violations"] or set(rec["data_reads"]) != want:
            raise SystemExit(f"{PREFIX} STOP {g} match reads {rec['data_reads']}; violations {rec['violations']}")
        files.update({n: sha256(run / n) for n in corr_files(g)})
        inputs[g] = {"calibration": {"path": str(SP.calibration_path(g)), "sha256": sha256(SP.calibration_path(g))},
                     "rgb_observation": {"path": str(SP.rgb_path(g)), "sha256": sha256(SP.rgb_path(g))}}
    fz = {"schema": "AB1d-correspondence-freeze-v1", "truth": SP.TRUTH_DERIVED,
          "statement": "NATURAL CORRESPONDENCE FREEZE: the three full-core matcher records and truth-stripped natural "
                       "products, frozen before any geometry and before any oracle or Position product is opened",
          "files": files, "matcher_inputs": inputs, "matcher_code": {n: sha256(REPO / n) for n in SP.MATCH_CODE},
          "matcher_config_sha256": SP.config_sha256(SP.MATCHER), "code": code_state(), "frozen_utc": utc()}
    write_json(path, fz)
    print(f"{PREFIX} freeze-correspondence: {len(files)} files hashed")
    return fz


def verify_correspondence_freeze(run: Path) -> dict:
    fz = read_json(run / "match/correspondence-freeze.json")
    want = {n for g in SP.GAZES for n in corr_files(g)}
    bad = [n for n, h in fz["files"].items() if sha256(run / n) != h]
    if bad or set(fz["files"]) != want:
        raise SystemExit(f"{PREFIX} STOP the natural correspondence freeze does not verify: {bad}")
    return fz


# ------------------------------------------------------------------ spherical geometry (section 16)
def run_spherical_gaze(calib_path: Path, product_path: Path, out_dir: Path, freeze_path: Path) -> dict:
    """The accepted AB1b spherical geometry (read-only) under an AB1d guard: exactly two data reads, no cv2."""
    if not Path(freeze_path).exists():
        raise RuntimeError("the natural correspondence product is not frozen")
    out_dir.mkdir(parents=True, exist_ok=True)
    g = OpenGuard("ab1d-spherical", [calib_path, product_path], [out_dir])
    try:
        with g:
            inputs = {"calibration": {"path": str(calib_path), "sha256": sha256(calib_path)},
                      "correspondences": {"path": str(product_path), "sha256": sha256(product_path)}}
            c = read_json(calib_path)
            FG.validate_calibration(c)
            prod = BG.load_product(product_path)
            rays = BG.left_core_rays(c)
            res = BG.compute_epipolar(c, prod)
            np.savez_compressed(out_dir / "left-core-rays.npz", **rays)
            np.savez_compressed(out_dir / "epipolar-result.npz", **res)
            summary = {"schema": "AB1d-spherical-summary-v1", "truth": SP.TRUTH_DERIVED,
                       "statement": "TRUTH-FREE SPHERICAL EPIPOLAR RECONSTRUCTION of the NATURAL correspondence "
                                    "(accepted AB1b geometry): the calibration and the frozen natural product only; no "
                                    "Position, Object Index, oracle or truth XYZ; no planar geometry",
                       "geometry": BG.SP.GEOMETRY, "geometry_config_sha256": BG.SP.config_sha256(BG.SP.GEOMETRY),
                       "inputs": inputs, "baseline_m": float(c["ipd_m"]), "focal_px": float(c["eyes"][0]["K"][0][0]),
                       **BG.summarize(c, rays, res)}
            write_json(out_dir / "spherical-summary.json", summary)
    finally:
        rec = g.record()
        rec["modules_loaded"] = {m: m in sys.modules for m in ("cv2", "fsg_stereo", "ab1d_match", "ab1c_planar",
                                                               "ab1b_oracle")}
        rec.update(truth_reads(rec["events"]))
        rec["truth_firewall_violations"] = len(rec["violations"])
        write_json(out_dir / "spherical-opened-files.json", rec)
    return summary


def spherical(run: Path) -> dict:
    once(run / "spherical" / SP.GAZES[0] / "epipolar-result.npz", "the spherical geometry")
    need(run / "match/correspondence-freeze.json", "freeze-correspondence")
    verify_sources()
    out = {}
    for g in SP.GAZES:
        summ = run_spherical_gaze(SP.calibration_path(g), run / "match" / g / "natural-correspondences.npz",
                                  run / "spherical" / g, run / "match/correspondence-freeze.json")
        rec = read_json(run / "spherical" / g / "spherical-opened-files.json")
        if rec["violations"] or any(rec["modules_loaded"].values()) or any(
                rec[k] for k in ("position_reads", "object_index_reads", "oracle_reads", "evaluation_reads")):
            raise SystemExit(f"{PREFIX} STOP {g} spherical guard: {rec['violations']}; modules {rec['modules_loaded']}")
        k, dd = summ["counts"], summ["distributions"]
        print(f"{PREFIX} spherical {g}: triangulated {k['triangulated_epipolar']:,}/{k['correspondences']:,}; |phi res| "
              f"max {dd['abs_phi_residual_rad']['max']:.2e}; kappa median {dd['kappa']['median']:.1f}; truth reads 0")
        out[g] = summ
    return out


def geom_files(g: str) -> list[str]:
    return [f"spherical/{g}/{n}" for n in ("left-core-rays.npz", "epipolar-result.npz", "spherical-summary.json",
                                           "spherical-opened-files.json")]


def freeze_geometry(run: Path) -> dict:
    path = run / "freeze/geometry-freeze.json"
    once(path, "the geometry freeze")
    for g in SP.GAZES:
        for n in geom_files(g):
            need(run / n, n)
    (run / "freeze").mkdir(parents=True, exist_ok=True)
    reads = ([run / "match/correspondence-freeze.json"] + [run / n for g in SP.GAZES for n in corr_files(g) + geom_files(g)]
             + [SP.calibration_path(g) for g in SP.GAZES])
    with OpenGuard("ab1d-freeze-geometry", reads, [run / "freeze"]) as gd:
        cfz = verify_correspondence_freeze(run)
        pre, files = {}, {}
        for g in SP.GAZES:
            prod = run / "match" / g / "natural-correspondences.npz"
            want = {str(SP.calibration_path(g).resolve()), str(prod.resolve())}
            sr = read_json(run / f"spherical/{g}/spherical-opened-files.json")
            ss = read_json(run / f"spherical/{g}/spherical-summary.json")
            p = {"spherical_reads_exactly_two": set(sr["data_reads"]) == want,
                 "violations_0": not sr["violations"],
                 "truth_reads_0": not any(sr[k] for k in ("position_reads", "object_index_reads", "oracle_reads",
                                                          "evaluation_reads")),
                 "no_cv2_no_matcher_no_planar": not any(sr["modules_loaded"].values()),
                 "frozen_product": ss["inputs"]["correspondences"]["sha256"] == cfz["files"][
                     f"match/{g}/natural-correspondences.npz"],
                 "same_calibration": ss["inputs"]["calibration"]["sha256"] == cfz["matcher_inputs"][g]["calibration"][
                     "sha256"]}
            if not all(p.values()):
                raise SystemExit(f"{PREFIX} STOP {g} geometry freeze preconditions: {p}")
            pre[g] = p
            files.update({n: sha256(run / n) for n in [f"match/{g}/natural-correspondences.npz"] + geom_files(g)})
        fz = {"schema": "AB1d-geometry-freeze-v1", "truth": SP.TRUTH_DERIVED,
              "statement": "GEOMETRY FREEZE: the truth-free spherical reconstruction of the natural correspondence of "
                           "all three gazes, frozen before any oracle or Position product is opened",
              "files": files, "calibrations": {g: {"path": str(SP.calibration_path(g)),
                                                   "sha256": sha256(SP.calibration_path(g))} for g in SP.GAZES},
              "correspondence_freeze_sha256": sha256(run / "match/correspondence-freeze.json"),
              "spherical_code": {n: sha256(REPO / n) for n in SP.SPHERICAL_CODE},
              "spherical_config_sha256": BG.SP.config_sha256(BG.SP.GEOMETRY), "preconditions": pre,
              "code": code_state(), "frozen_utc": utc()}
        write_json(path, fz)
    rec = gd.record()
    rec["truth_firewall_violations"] = len(rec["violations"])
    rec.update(truth_reads(rec["events"]))
    write_json(run / "freeze/geometry-freeze-opened-files.json", rec)
    print(f"{PREFIX} freeze-geometry: {len(files)} files hashed; spherical read exactly the calibration and the frozen "
          f"natural product; truth reads 0")
    return fz


def verify_geometry_freeze(run: Path) -> dict:
    fz = read_json(run / "freeze/geometry-freeze.json")
    want = {n for g in SP.GAZES for n in [f"match/{g}/natural-correspondences.npz"] + geom_files(g)}
    bad = [n for n, h in fz["files"].items() if sha256(run / n) != h]
    bad += [g for g, v in fz["calibrations"].items() if sha256(v["path"]) != v["sha256"]]
    if bad or set(fz["files"]) != want:
        raise SystemExit(f"{PREFIX} STOP the frozen geometry does not verify: {bad}")
    return fz


# ------------------------------------------------------------------ evaluation (sections 17-22; post-freeze)
def bench_files(g: str) -> list[Path]:
    return [SP.oracle_path(g), SP.perfect_path(g), SP.reference_path(g)]


def verify_bench() -> dict:
    out = {}
    for g in SP.GAZES:
        for p in bench_files(g):
            rel = str(p.relative_to(SP.A1C_RUN))
            h = sha256(p)
            if h != SP.BENCH_PINS[rel]:
                raise SystemExit(f"{PREFIX} STOP benchmark file changed: {rel}")
            out[rel] = h
    return out


def frac_le(a, edges) -> dict | None:
    a = np.asarray(a, np.float64)
    a = a[np.isfinite(a)]
    if a.size == 0:
        return None
    return {f"{e:g}": float((a <= e).mean()) for e in edges}


def strata(values, err_px, top1, nan_label: str) -> dict:
    """Error stratified by quartiles of ``values`` on the evaluable set; NaN values form their own stratum."""
    values, err_px, top1 = np.asarray(values, np.float64), np.abs(np.asarray(err_px, np.float64)), np.asarray(top1, bool)
    fin = np.isfinite(values)
    out = {"edges": None, "bins": []}
    if fin.sum() >= 4:
        q25, q50, q75 = (float(np.quantile(values[fin], x)) for x in (0.25, 0.5, 0.75))
        out["edges"] = [q25, q50, q75]
        masks = [("Q1", fin & (values <= q25)), ("Q2", fin & (values > q25) & (values <= q50)),
                 ("Q3", fin & (values > q50) & (values <= q75)), ("Q4", fin & (values > q75))]
    else:
        masks = []
    masks.append((nan_label, ~fin))
    for name, m in masks:
        e = err_px[m]
        out["bins"].append({"stratum": name, "count": int(m.sum()),
                            "median_abs_px": float(np.median(e)) if e.size else None,
                            "p90_abs_px": float(np.quantile(e, 0.9)) if e.size else None,
                            "within_0.25px": float((e <= 0.25).mean()) if e.size else None,
                            "within_1px": float((e <= 1.0).mean()) if e.size else None,
                            "oracle_top1": float(top1[m].mean()) if e.size else None})
    return out


def evaluation_core(c: dict, rec: dict, geo: dict, ora: dict, perf: dict, pos_l: np.ndarray, ctx, M) -> tuple:
    n = SP.CORE_SIZE ** 2
    core = (np.asarray(rec["left_core_row"], np.int64) * SP.CORE_SIZE + np.asarray(rec["left_core_col"], np.int64))
    if not np.array_equal(core, np.arange(n)):
        raise SystemExit(f"{PREFIX} STOP the matcher record is not the full core in order")
    oi = np.asarray(ora["left_core_row"], np.int64) * SP.CORE_SIZE + np.asarray(ora["left_core_col"], np.int64)
    ov = np.zeros(n, bool)
    ov[oi] = True
    nv = np.asarray(rec["valid_match"], bool)
    ev = ov & nv
    cls = np.where(ov & nv, 0, np.where(ov, 1, np.where(nv, 2, 3))).astype(np.int8)
    e_idx = np.nonzero(ev)[0]
    uv_or = np.full((n, 2), np.nan)
    uv_or[oi] = ora["uv_R"]
    th_or = BG.theta_phi(FG.rays_h(c["eyes"][1], uv_or[e_idx]))[0]
    th_est = rec["theta_R_est"][e_idx]
    e_th = th_est - th_or
    # ORACLE-ON-CURVE: (theta_R_oracle, phi_L) on the matcher's exact plane
    ph_l = rec["phi_L"][e_idx]
    qu, qv, _ = M.project(ctx.cam_r, *M.direction(th_or, ph_l))
    q_oc = np.stack([qu, qv], -1)
    q_inf, t = rec["q_inf"][e_idx], rec["line_dir"][e_idx]
    s_oc = np.sum((q_oc - q_inf) * t, -1)
    perp = np.abs((q_oc - q_inf)[:, 0] * (-t[:, 1]) + (q_oc - q_inf)[:, 1] * t[:, 0])
    scale = M.line_theta(ctx, e_idx, s_oc + 0.5) - M.line_theta(ctx, e_idx, s_oc - 0.5)
    e_px = e_th / scale
    e_f = ctx.cam_r.f * e_th
    e_s = rec["s_est"][e_idx] - s_oc
    s_or, ex_or, std_or = M.score_at(ctx, e_idx, th_or)
    best = rec["best_zncc"][e_idx]
    diff = s_or - best
    at_best = s_or >= best - SP.AT_BEST_TOL
    pk = rec["peak_s"][e_idx]
    within = np.abs(pk - s_oc[:, None]) <= SP.ORACLE_PEAK_RADIUS_PX
    rank = np.where(within.any(axis=1), np.argmax(within, axis=1) + 1, SP.TOP_K + 1).astype(np.int8)
    outside = (s_oc < rec["k_first"][e_idx]) | (s_oc > rec["k_last"][e_idx])
    offs = np.stack([M.score_at(ctx, e_idx, M.line_theta(ctx, e_idx, s_oc + o))[0] for o in SP.LANDSCAPE_OFFSETS_PX], 1)
    # metric consequence
    gi = np.asarray(geo["left_core_row"], np.int64) * SP.CORE_SIZE + np.asarray(geo["left_core_col"], np.int64)
    p_nat_full = np.full((n, 3), np.nan)
    p_nat_full[gi] = geo["P_epi"]
    kap_full = np.full(n, np.nan)
    kap_full[gi] = geo["kappa"]
    pi = np.asarray(perf["left_core_row"], np.int64) * SP.CORE_SIZE + np.asarray(perf["left_core_col"], np.int64)
    p_perf_full = np.full((n, 3), np.nan)
    p_perf_full[pi] = perf["P_epi"]
    p_nat, p_perf = p_nat_full[e_idx], p_perf_full[e_idx]
    rows, cols = e_idx // SP.CORE_SIZE + SP.CORE_ORIGIN, e_idx % SP.CORE_SIZE + SP.CORE_ORIGIN
    p_ref = FG.world_to_head(c, np.asarray(pos_l)[rows, cols].astype(np.float64))
    o_l = np.asarray(c["eyes"][0]["centre_h_m"], np.float64)
    out_metric = {}
    arrs = {}
    for name, p_b in (("vs_perfect", p_perf), ("vs_position", p_ref)):
        e3 = np.linalg.norm(p_nat - p_b, axis=-1)
        rb = np.linalg.norm(p_b - o_l, axis=-1)
        rad = np.linalg.norm(p_nat - o_l, axis=-1) - rb
        rel = np.abs(rad) / rb
        out_metric[name] = {"pairs": int(e3.size), "error_3d_m": qd(e3), "radial_abs_m": qd(np.abs(rad)),
                            "radial_signed_m": qd(rad), "range_relative": qd(rel),
                            "fraction_3d_within_m": frac_le(e3, SP.METRIC_FRACTIONS_M)}
        arrs[f"error_3d_{name}_m"] = e3
        arrs[f"radial_signed_{name}_m"] = rad
    top1 = rank == 1
    summ = {
        "counts": {"left_core": n, "oracle_correspondences": int(ov.sum()), "natural_valid": int(nv.sum()),
                   "evaluable": int(ev.sum()), "coverage": float(ev.sum() / max(ov.sum(), 1)),
                   "natural_valid_non_oracle": int((~ov & nv).sum()), "oracle_visible_natural_invalid": int((ov & ~nv).sum()),
                   "oracle_visible_natural_invalid_by_reason": {SP.REASONS[k]: int((ov & ~nv & (rec["reason"] == k)).sum())
                                                                for k in SP.REASONS},
                   "neither": int((~ov & ~nv).sum())},
        "primary": {"e_theta_signed_rad": qd(e_th), "e_theta_abs_rad": qd(np.abs(e_th)),
                    "px_equivalent_signed": qd(e_px), "px_equivalent_abs": qd(np.abs(e_px)),
                    "px_equivalent_fractions": frac_le(np.abs(e_px), SP.PX_BINS),
                    "focal_approximation_abs_px": qd(np.abs(e_f)),
                    "line_coordinate_difference_abs_px": qd(np.abs(e_s)),
                    "local_scale_rad_per_px": qd(scale), "oracle_on_curve_perpendicular_px": qd(perp)},
        "landscape": {"oracle_zncc": qd(s_or), "best_zncc": qd(best), "oracle_minus_best": qd(diff),
                      "oracle_at_or_above_best": float(np.mean(at_best[np.isfinite(s_or)])) if np.isfinite(s_or).any()
                      else None,
                      "oracle_unscorable": int((~np.isfinite(s_or)).sum()),
                      "oracle_outside_segment": int(outside.sum()),
                      "rank_counts": {str(r): int((rank == r).sum()) for r in range(1, SP.TOP_K + 2)},
                      "top_fractions": {f"top{k}": float((rank <= k).mean()) for k in SP.TOPK_FRACTIONS}
                      | {"worse_than_top8": float((rank > SP.TOP_K).mean())},
                      "offsets_px": list(SP.LANDSCAPE_OFFSETS_PX),
                      "offset_median_zncc": [float(np.nanmedian(offs[:, j])) for j in range(offs.shape[1])],
                      "offset_median_minus_zero": [float(np.nanmedian(offs[:, j] - offs[:, 2]))
                                                   for j in range(offs.shape[1])],
                      "fraction_zero_offset_is_max": float(np.mean(np.nanargmax(np.where(np.isnan(offs), -np.inf, offs),
                                                                               axis=1) == 2))},
        "metric": out_metric | {"natural_kappa": qd(kap_full[e_idx])},
        "confidence": {
            "peak_margin": strata(rec["peak_margin"][e_idx], e_px, top1, "single peak"),
            "left_patch_std_u8": strata(rec["left_patch_std_u8"][e_idx], e_px, top1, "n/a"),
            "best_zncc": strata(best, e_px, top1, "n/a"),
            "peak_curvature": strata(rec["peak_curvature"][e_idx], e_px, top1, "unrefined"),
            "candidate_count": strata(rec["candidate_count"][e_idx].astype(np.float64), e_px, top1, "n/a")},
    }
    arrs.update({"class_map": cls, "core_index": e_idx.astype(np.int32), "theta_R_oracle": th_or, "e_theta": e_th,
                 "s_oracle_on_curve": s_oc, "oracle_perpendicular_px": perp, "local_scale_rad_per_px": scale,
                 "e_px": e_px, "e_focal_px": e_f, "e_line_px": e_s, "zncc_oracle": s_or, "oracle_patch_exists": ex_or,
                 "oracle_patch_std": std_or, "oracle_rank": rank, "oracle_outside_segment": outside,
                 "zncc_offsets": offs, "P_natural": p_nat, "P_perfect": p_perf, "P_reference": p_ref})
    return summ, arrs


def pooled(arrs: list[dict], recs: list[dict]) -> dict:
    e = np.concatenate([a["e_theta"] for a in arrs])
    px = np.concatenate([a["e_px"] for a in arrs])
    rank = np.concatenate([a["oracle_rank"] for a in arrs])
    out = {"evaluable": int(e.size), "e_theta_abs_rad": qd(np.abs(e)), "px_equivalent_abs": qd(np.abs(px)),
           "px_equivalent_fractions": frac_le(np.abs(px), SP.PX_BINS),
           "top_fractions": {f"top{k}": float((rank <= k).mean()) for k in SP.TOPK_FRACTIONS}
           | {"worse_than_top8": float((rank > SP.TOP_K).mean())}}
    for name in ("vs_perfect", "vs_position"):
        e3 = np.concatenate([a[f"error_3d_{name}_m"] for a in arrs])
        out[name] = {"error_3d_m": qd(e3), "fraction_3d_within_m": frac_le(e3, SP.METRIC_FRACTIONS_M)}
    pm = np.concatenate([r["peak_margin"][a["core_index"]] for a, r in zip(arrs, recs)])
    top1 = rank == 1
    out["confidence_peak_margin"] = strata(pm, px, top1, "single peak")
    ls = np.concatenate([r["left_patch_std_u8"][a["core_index"]] for a, r in zip(arrs, recs)])
    out["confidence_left_texture"] = strata(ls, px, top1, "n/a")
    return out


def evaluation_files() -> list[str]:
    return ["evaluation/evaluation-summary.json", "evaluation/evaluation-opened-files.json"] + [
        f"evaluation/{g}/evaluation-result.npz" for g in SP.GAZES]


def evaluate(run: Path) -> dict:
    out = run / "evaluation"
    once(out / "evaluation-summary.json", "the evaluation")
    need(run / "freeze/geometry-freeze.json", "freeze-geometry")
    out.mkdir(parents=True, exist_ok=True)
    frozen = ([run / "freeze/geometry-freeze.json", run / "match/correspondence-freeze.json"]
              + [run / n for g in SP.GAZES for n in corr_files(g) + geom_files(g)]
              + [SP.calibration_path(g) for g in SP.GAZES] + [SP.rgb_path(g) for g in SP.GAZES])
    refs = [p for g in SP.GAZES for p in bench_files(g)]
    import ab1d_match as M
    with OpenGuard("ab1d-evaluation", frozen + refs, [out]) as gd:
        verify_correspondence_freeze(run)
        verify_geometry_freeze(run)
        gd.mark("freezes_verified")
        data = {}
        for g in SP.GAZES:
            c = read_json(SP.calibration_path(g))
            obs = load_npz(SP.rgb_path(g))
            data[g] = (c, load_npz(run / "match" / g / "matcher-record.npz"),
                       load_npz(run / "spherical" / g / "epipolar-result.npz"), obs)
        gd.mark("reference_access_begins")
        bench = verify_bench()
        per, arrs, recs = {}, [], []
        for g in SP.GAZES:
            c, rec, geo, obs = data[g]
            ora = load_npz(SP.oracle_path(g))
            perf = load_npz(SP.perfect_path(g))
            with np.load(SP.reference_path(g), allow_pickle=False) as z:
                pos_l = np.asarray(z["position_w_L"])
            ctx = M.Context(c, M.gray(obs["rgb_L"]), M.gray(obs["rgb_R"]))
            summ, arr = evaluation_core(c, rec, geo, ora, perf, pos_l, ctx, M)
            (out / g).mkdir(parents=True, exist_ok=True)
            np.savez_compressed(out / g / "evaluation-result.npz", **arr)
            per[g] = summ
            arrs.append(arr)
            recs.append(rec)
            p, ln, mt = summ["primary"], summ["landscape"], summ["metric"]
            print(f"{PREFIX} evaluate {g}: evaluable {summ['counts']['evaluable']:,} / oracle "
                  f"{summ['counts']['oracle_correspondences']:,} (coverage {summ['counts']['coverage']:.3f}); "
                  f"|px-eq| median {p['px_equivalent_abs']['median']:.3f} p95 {p['px_equivalent_abs']['p95']:.2f}; "
                  f"top1 {ln['top_fractions']['top1']:.3f}; vs perfect 3-D median "
                  f"{mt['vs_perfect']['error_3d_m']['median'] * 1e3:.2f} mm, <=12 mm "
                  f"{mt['vs_perfect']['fraction_3d_within_m']['0.012']:.3f}")
        summary = {"schema": "AB1d-evaluation-summary-v1", "truth": SP.TRUTH_REFERENCE,
                   "statement": "REFERENCE / EVALUATION: after both freezes, the natural correspondence is scored against "
                                "the AB1c perfect correspondence (benchmark only) and the metric consequence against the "
                                "AB1c perfect spherical reconstruction and Blender Position; descriptive only",
                   "benchmark_files": bench, "per_gaze": per, "pooled": pooled(arrs, recs),
                   "constants": {"oracle_peak_radius_px": SP.ORACLE_PEAK_RADIUS_PX,
                                 "landscape_offsets_px": list(SP.LANDSCAPE_OFFSETS_PX), "at_best_tol": SP.AT_BEST_TOL,
                                 "px_bins": list(SP.PX_BINS), "metric_fractions_m": list(SP.METRIC_FRACTIONS_M)},
                   "code": code_state()}
        write_json(out / "evaluation-summary.json", summary)
    rec_g = gd.record()
    rec_g["truth_firewall_violations"] = len(rec_g["violations"])
    write_json(out / "evaluation-opened-files.json", rec_g)
    return summary


# ------------------------------------------------------------------ manifest / CLI
def write_manifest(run: Path) -> dict:
    files = sorted(str(p.relative_to(run)) for p in run.rglob("*") if p.is_file()
                   and p.name not in ("manifest.json", "check-summary.json", "process-log.jsonl")
                   and "synthetic/guard-probe" not in str(p.relative_to(run)))
    m = {"schema": "AB1d-manifest-v1", "experiment": SP.EXPERIMENT, "contract": SP.CONTRACT, "code": code_state(),
         "base_commit": SP.BASE_COMMIT, "a1c_run": str(SP.A1C_RUN), "truth": TRUTH_CLASSES,
         "files": {f: sha256(run / f) for f in files}}
    write_json(run / "manifest.json", m)
    return m


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in SP.COMMANDS:
        p = sub.add_parser(name)
        p.add_argument("--run", required=True, type=Path)
        if name == "visualize":
            p.add_argument("--visuals", required=True, type=Path)
    a = ap.parse_args(argv)
    run = a.run.resolve()
    t0 = time.time()
    status = "failed"
    try:
        if a.cmd == "synthetic":
            ok = synthetic(run)["passed"]
            status = "ok" if ok else "failed"
            return 0 if ok else 1
        if a.cmd in SP.CANONICAL:
            require_committed(a.cmd)
        {"source": source, "match": match, "freeze-correspondence": freeze_correspondence, "spherical": spherical,
         "freeze-geometry": freeze_geometry, "evaluate": evaluate}.get(a.cmd, lambda r: None)(run)
        if a.cmd == "visualize":
            import ab1d_visuals
            ab1d_visuals.visualize(run, a.visuals.resolve())
            write_manifest(run)
        status = "ok"
        return 0
    finally:
        log_process(run, a.cmd, t0, status)


if __name__ == "__main__":
    raise SystemExit(main())
