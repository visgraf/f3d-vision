"""Active Bootstrap-1d3: one-shot SGBM viability (run order and truth boundary).

Contract: docs/active-bootstrap/ab1d3-sgbm-viability-contract.md.

    .venv/bin/python tools/active_bootstrap/ab1d3_run.py source                --run RUN
    .venv/bin/python tools/active_bootstrap/ab1d3_run.py preflight             --run RUN
    .venv/bin/python tools/active_bootstrap/ab1d3_run.py sgbm                  --run RUN
    .venv/bin/python tools/active_bootstrap/ab1d3_run.py raw-core-adapter      --run RUN
    .venv/bin/python tools/active_bootstrap/ab1d3_run.py freeze-correspondence --run RUN
    .venv/bin/python tools/active_bootstrap/ab1d3_run.py spherical             --run RUN
    .venv/bin/python tools/active_bootstrap/ab1d3_run.py freeze-geometry       --run RUN
    .venv/bin/python tools/active_bootstrap/ab1d3_run.py evaluate              --run RUN
    .venv/bin/python tools/active_bootstrap/ab1d3_run.py visualize             --run RUN --visuals VIS

No render and no Blender: the three accepted AB1d2 4096-spp observations are read in place.  ``sgbm`` runs the ONE
frozen SGBM configuration (``ab1d3_sgbm.compute_sgbm``: the accepted ``ab1a_stereo.compute_natural``, unchanged, on the
full rectified raster) under an allowlist guard that admits exactly the calibration and the RGB observation of each gaze.
``raw-core-adapter`` maps the refined disparity back to the raw left core and writes the accepted AB1b truth-free product.
``spherical`` runs the accepted AB1b geometry (``ab1d_run.run_spherical_gaze``).  Only after the geometry freeze does
``evaluate`` open the accepted AB1c benchmark and the accepted AB1d2 evaluation (REFERENCE / EVALUATION).  This module
imports neither cv2 nor the SGBM module at load time, so the spherical stage loads no matcher.
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
import ab1d_run as AD  # noqa: E402  (accepted AB1d run helpers: run_spherical_gaze, read-only)
import ab1d3_spec as SP  # noqa: E402
import fsg_geometry as FG  # noqa: E402  (accepted, read-only)
from nb1a_guard import OpenGuard  # noqa: E402  (accepted, read-only)

PREFIX = "[ab1d3]"
TRUTH_CLASSES = {"ORACLE INPUT": "the accepted AB1d2 4096-spp RGB observations",
                 "DERIVED": "the SGBM records, the raw-core adapter and its truth-free product, the spherical geometry, "
                            "synthetic known answers",
                 "REFERENCE / EVALUATION": "the accepted AB1c perfect correspondence (benchmark only), the AB1c perfect "
                                           "spherical reconstruction, Blender Position and the accepted AB1d2 primitive "
                                           "evaluation, opened only after the geometry freeze"}


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


def verify_pins(root: Path, pins: dict) -> dict:
    return {p: (sha256(root / p) if (root / p).is_file() else None) for p, h in pins.items()
            if not (root / p).is_file() or sha256(root / p) != h}


def verify_sources() -> None:
    bad = verify_pins(REPO, SP.SOURCE_PINS)
    if bad:
        raise SystemExit(f"{PREFIX} STOP accepted sources changed: {bad}")


def verify_observations() -> dict:
    bad = verify_pins(SP.A1D2_RUN, SP.OBS_PINS)
    if bad:
        raise SystemExit(f"{PREFIX} STOP the accepted 4096-spp observations changed: {bad}")
    return dict(SP.OBS_PINS)


def bench_pins() -> dict:
    import ab1d_spec as DS
    return dict(DS.BENCH_PINS)


def bench_paths(g: str) -> list[Path]:
    import ab1d_spec as DS
    return [DS.oracle_path(g), DS.perfect_path(g), DS.reference_path(g)]


def a1d2_eval_rel(g: str) -> str:
    return f"evaluation/{g}/evaluation-result.npz"


# ------------------------------------------------------------------ source (section 4)
def source(run: Path) -> dict:
    out = run / "source/source-manifest.json"
    once(out, "the source manifest")
    verify_sources()
    import ab1a_spec as AS
    import ab1b_spec as BS
    import ab1d2_spec as D2
    import fsg_stereo as FS
    remote = git("remote", "get-url", "origin")
    obs = verify_observations()
    a1d2_man = read_json(SP.a1d2("manifest.json"))["files"]
    a1c_man = read_json(SP.a1c(SP.A1C_MANIFEST[0]))["files"]
    ofz = read_json(SP.a1d2("freeze/observation-freeze.json"))
    ctl = read_json(SP.a1d2("observations/render-control.json"))
    direct = {k: h for k, h in SP.A1D2_PINS.items() if not k.startswith("evaluation/")}
    cal = {}
    for g in SP.GAZES:
        c = read_json(SP.calibration_path(g))
        r = FS.rectification(c)
        cal[g] = {"depth_search_z_rect_m": c["depth_search_z_rect_m"], "num_disparities": int(r["num_disparities"]),
                  "min_disparity": int(r["min_disparity"]), "focal_px": c["eyes"][0]["K"][0][0], "ipd_m": c["ipd_m"],
                  "gaze_yaw_pitch_deg": c["gaze_yaw_pitch_deg"], "image_size_wh": c["image_size_wh"]}
    try:
        accepted_ancestor = subprocess.run(["git", "merge-base", "--is-ancestor", SP.AB1D2_ACCEPTANCE, "HEAD"],
                                           cwd=REPO).returncode == 0
    except OSError:
        accepted_ancestor = False
    report = (REPO / SP.AB1D2_REPORT).read_text()
    ident = {
        "canonical_remote": remote.rstrip("/").removesuffix(".git").endswith(SP.CANONICAL_REMOTE),
        "ab1d2_acceptance_ancestor": accepted_ancestor,
        "ab1d2_accepted_marker": SP.AB1D2_ACCEPTED_MARKER in report and "**Status: ACCEPTED.**" in report,
        "observation_files": True,
        "observations_in_ab1d2_manifest": all(a1d2_man.get(k) == h for k, h in obs.items()),
        "observations_in_observation_freeze": all(ofz["files"].get(k) == h for k, h in obs.items()),
        "observation_freeze_rgb_and_calibration": all(
            ofz["rgb_observations"][g] == obs[SP.obs_rel(g, "rgb-observation.npz")]
            and ofz["calibrations"][g] == obs[SP.obs_rel(g, "calibration.json")] for g in SP.GAZES),
        "observation_freeze_spp": ofz["spp"] == SP.SPP,
        "render_control_ok": bool(ctl["ok"]),
        "ab1d2_direct_files": not verify_pins(SP.A1D2_RUN, direct),
        "ab1d2_pins_in_manifest": all(a1d2_man.get(k) == h for k, h in SP.A1D2_PINS.items() if k != "manifest.json"),
        "ab1d2_visuals_manifest": sha256(SP.A1D2_VIS_MANIFEST[0]) == SP.A1D2_VIS_MANIFEST[1],
        "ab1c_manifest": sha256(SP.a1c(SP.A1C_MANIFEST[0])) == SP.A1C_MANIFEST[1],
        "ab1c_benchmark_in_manifest": all(a1c_man.get(k) == h for k, h in bench_pins().items()),
        "ab1d2_gazes": D2.GAZE_TABLE == SP.GAZE_TABLE,
        "fsg_constants": (FS.BLOCK_SIZE, FS.UNIQUENESS_RATIO, FS.LR_TOLERANCE_PX, FS.MIN_LOCAL_STD_U8)
                         == (SP.SGBM["blockSize"], SP.SGBM["uniquenessRatio"], SP.SGBM["lr_tolerance_px"],
                             SP.SGBM["min_local_std_u8"]),
        "ab1a_matcher": (AS.MATCHER["block_size"] == SP.SGBM["blockSize"] and AS.MATCHER["identity_guard"] is None
                         and tuple(AS.TERMS) == SP.TERMS and list(AS.Z_RECT_M) == SP.SGBM["z_rect_m"]
                         and AS.MATCHER["refinement"]["iterations"] == SP.SGBM["refinement"]["iterations"]
                         and AS.MATCHER["refinement"]["max_step_px"] == SP.SGBM["refinement"]["max_step_px"]
                         and AS.MATCHER["refinement"]["max_total_px"] == SP.SGBM["refinement"]["max_total_px"]),
        "calibrations": all(v["depth_search_z_rect_m"] == SP.SGBM["z_rect_m"] and v["num_disparities"] == SP.NUM_DISPARITIES
                            and v["min_disparity"] == SP.SGBM["minDisparity_left"] and v["focal_px"] == SP.FOCAL_PX
                            and v["ipd_m"] == SP.IPD_M and v["image_size_wh"] == [SP.RAW_SIZE, SP.RAW_SIZE]
                            and v["gaze_yaw_pitch_deg"] == [SP.GAZE_TABLE[g]["yaw_deg"], SP.GAZE_TABLE[g]["pitch_deg"]]
                            for g, v in cal.items()),
        "ab1b_constants": BS.CORE_SIZE == SP.CORE_SIZE and BS.CORE_ORIGIN == SP.CORE_ORIGIN
                          and tuple(BS.PRODUCT_KEYS) == ("left_core_row", "left_core_col", "uv_L", "uv_R"),
    }
    if not all(ident.values()):
        raise SystemExit(f"{PREFIX} STOP source identity: {ident}")
    rec = {"schema": "AB1d3-source-manifest-v1", "truth": SP.TRUTH_DERIVED, "experiment": SP.EXPERIMENT,
           "statement": "pinned sources verified; the three accepted AB1d2 4096-spp observations are reused exactly (no "
                        "render); the AB1c benchmark and the AB1d2 evaluation are verified here only through their "
                        "manifests and are hashed again, then opened, only after the geometry freeze",
           "remote": remote, "identity": ident, "a1d2_run": str(SP.A1D2_RUN), "a1c_run": str(SP.A1C_RUN),
           "observations": obs, "a1d2_pins": SP.A1D2_PINS, "a1c_benchmark_pins": bench_pins(),
           "calibration_only": cal, "sgbm": SP.SGBM, "sgbm_config_sha256": SP.config_sha256(SP.SGBM),
           "adapter": SP.ADAPTER, "adapter_config_sha256": SP.config_sha256(SP.ADAPTER), "source_pins": SP.SOURCE_PINS,
           "base_commit": SP.BASE_COMMIT, "ab1d2_acceptance": SP.AB1D2_ACCEPTANCE,
           "contract_commit": SP.CONTRACT_COMMIT, "code": code_state(), "created_utc": utc()}
    write_json(out, rec)
    print(f"{PREFIX} source: {len(SP.SOURCE_PINS)} code pins, {len(obs)} AB1d2 observation pins, {len(SP.A1D2_PINS)} "
          f"AB1d2 run pins, {len(bench_pins())} AB1c benchmark pins (manifest only); numDisparities "
          f"{SP.NUM_DISPARITIES} at every gaze; canonical remote and AB1d2 acceptance verified")
    return rec


# ------------------------------------------------------------------ preflight (sections 9, 10)
def preflight(run: Path) -> dict:
    import ab1d3_synthetic as SY
    out = run / "preflight"
    rep = SY.run_preflight(out)
    rep["code"] = code_state()
    write_json(out / "preflight-report.json", rep)
    for x in rep["cases"]:
        print(f"{PREFIX} preflight {'PASS' if x['passed'] else 'FAIL'} {x['case']:>3} {x['name']}")
    print(f"{PREFIX} {'AB1D3_PREFLIGHT_PASS' if rep['passed'] else 'PREFLIGHT FAILED'} "
          f"{sum(x['passed'] for x in rep['cases'])}/{len(rep['cases'])} in {rep['seconds']} s")
    return rep


def same_commit_report(path: Path, what: str, cs: dict) -> dict:
    need(path, what)
    rep = read_json(path)
    if not rep["passed"] or rep["code"]["commit"] != cs["commit"] or rep["code"]["dirty"]:
        raise SystemExit(f"{PREFIX} STOP {what} must pass from this exact clean commit ({cs['commit']})")
    return rep


# ------------------------------------------------------------------ sgbm (section 6)
def sgbm_guard_ok(run: Path, g: str) -> tuple[bool, dict]:
    rec = read_json(run / "sgbm" / g / "sgbm-opened-files.json")
    want = {str(SP.calibration_path(g).resolve()), str(SP.rgb_path(g).resolve())}
    p = {"reads_exactly_calibration_and_rgb": set(rec["data_reads"]) == want, "violations_0": not rec["violations"],
         "modules_not_loaded": not any(rec["modules_loaded"].values()),
         "truth_reads_0": not any(rec[k] for k in ("position_reads", "object_index_reads", "oracle_reads",
                                                   "evaluation_or_matcher_product_reads"))}
    return all(p.values()), p


def calls_ok(calls: dict) -> tuple[bool, dict]:
    """The recorded OpenCV calls are exactly the frozen configuration (section 6d)."""
    c = calls["calls"]
    sg = c["StereoSGBM_create"]
    getters_ok = len(sg) == 2 and all(
        {k: e["getters"][k] for k in SP.SGBM_GETTERS} == SP.SGBM_GETTERS for e in sg) and [
        e["getters"]["getMinDisparity"] for e in sg] == [SP.SGBM_MIN_DISPARITY["L"], SP.SGBM_MIN_DISPARITY["R"]]
    full = all(len(e["compute"]) == 1 and e["compute"][0]["left_shape"] == [SP.RAW_SIZE, SP.RAW_SIZE]
               and e["compute"][0]["right_shape"] == [SP.RAW_SIZE, SP.RAW_SIZE]
               and e["compute"][0]["left_dtype"] == "uint8" and e["compute"][0]["right_dtype"] == "uint8" for e in sg)
    lr_pair = len(sg) == 2 and (sg[0]["compute"][0]["left_sha256"] == sg[1]["compute"][0]["right_sha256"]
                                and sg[0]["compute"][0]["right_sha256"] == sg[1]["compute"][0]["left_sha256"])
    rect = c["stereoRectify"]
    rect_ok = len(rect) == 1 and rect[0]["flags"] == SP.RECTIFY["flags"] and rect[0]["alpha"] == SP.RECTIFY["alpha"] \
        and rect[0]["newImageSize"] == SP.RECTIFY["newImageSize"]
    p = {"sgbm_getters_frozen": getters_ok, "full_raster_uint8": full, "left_right_then_right_left": lr_pair,
         "rectification": rect_ok, "maps_2": len(c["initUndistortRectifyMap"]) == 2,
         "roi_1": len(c["getValidDisparityROI"]) == 1, "tripwires_0": not calls["tripwire_calls"]}
    return all(p.values()), p


def sgbm(run: Path) -> dict:
    cs = code_state()
    once(run / "sgbm" / SP.GAZES[0] / "sgbm-record.npz", "the canonical SGBM")
    need(run / "source/source-manifest.json", "source")
    same_commit_report(run / "preflight/preflight-report.json", "preflight", cs)
    verify_sources()
    verify_observations()
    import ab1d3_sgbm as SG
    out = {}
    for g in SP.GAZES:
        summ = SG.run_sgbm_gaze(SP.calibration_path(g), SP.rgb_path(g), run / "sgbm" / g)
        ok, p = sgbm_guard_ok(run, g)
        cok, cp = calls_ok(read_json(run / "sgbm" / g / "sgbm-calls.json"))
        if not ok or not cok:
            raise SystemExit(f"{PREFIX} STOP {g} sgbm guard / configuration: {p} {cp}")
        r = summ["raster"]
        print(f"{PREFIX} sgbm {g}: full raster {r['pixels']:,}; SGBM-left valid {r['sgbm_left_valid']:,}; full validity "
              f"{r['valid']:,}; {summ['seconds']:.3f} s; reads exactly calibration + 4096 RGB; frozen configuration "
              f"recorded; truth reads 0")
        out[g] = summ
    return out


# ------------------------------------------------------------------ raw-core adapter (section 8)
def adapter_guard_ok(run: Path, g: str) -> tuple[bool, dict]:
    rec = read_json(run / "correspondence" / g / "adapter-opened-files.json")
    want = {str(SP.calibration_path(g).resolve()), str((run / "sgbm" / g / "sgbm-record.npz").resolve())}
    p = {"reads_exactly_calibration_and_sgbm_record": set(rec["data_reads"]) == want,
         "violations_0": not rec["violations"], "modules_not_loaded": not any(rec["modules_loaded"].values()),
         "truth_reads_0": not any(rec[k] for k in ("position_reads", "object_index_reads", "oracle_reads",
                                                   "evaluation_or_matcher_product_reads"))}
    return all(p.values()), p


def raw_core_adapter(run: Path) -> dict:
    once(run / "correspondence" / SP.GAZES[0] / "sgbm-correspondences.npz", "the raw-core adapter")
    for g in SP.GAZES:
        need(run / "sgbm" / g / "sgbm-record.npz", "sgbm")
    verify_sources()
    import ab1d3_sgbm as SG
    out = {}
    for g in SP.GAZES:
        summ = SG.run_adapter_gaze(SP.calibration_path(g), run / "sgbm" / g / "sgbm-record.npz", run / "correspondence" / g)
        ok, p = adapter_guard_ok(run, g)
        if not ok or not summ["footprint_full_valid_equals_valid_mask"]:
            raise SystemExit(f"{PREFIX} STOP {g} adapter guard: {p}")
        att = {a["stage"]: a["remaining"] for a in summ["attrition"]}
        print(f"{PREFIX} raw-core-adapter {g}: raw core {att['raw_core']:,} -> rectifiable {att['rectifiable']:,} -> "
              f"footprint SGBM-left {att['footprint_term_sgbm_left']:,} -> full validity {att['footprint_term_roi']:,} -> "
              f"raw inside {att['raw_inside']:,} = product {summ['counts']['product_pairs']:,}; truth reads 0")
        out[g] = summ
    return out


def corr_files(g: str) -> list[str]:
    return ([f"sgbm/{g}/{n}" for n in ("sgbm-record.npz", "sgbm-summary.json", "sgbm-calls.json", "sgbm-opened-files.json")]
            + [f"correspondence/{g}/{n}" for n in ("adapter-record.npz", "sgbm-correspondences.npz",
                                                   "adapter-summary.json", "adapter-opened-files.json")])


def freeze_correspondence(run: Path) -> dict:
    path = run / "correspondence/correspondence-freeze.json"
    once(path, "the SGBM correspondence freeze")
    files, inputs, guards = {}, {}, {}
    for g in SP.GAZES:
        for n in corr_files(g):
            need(run / n, n)
        ok1, p1 = sgbm_guard_ok(run, g)
        ok2, p2 = adapter_guard_ok(run, g)
        ok3, p3 = calls_ok(read_json(run / f"sgbm/{g}/sgbm-calls.json"))
        if not (ok1 and ok2 and ok3):
            raise SystemExit(f"{PREFIX} STOP {g} guards before the correspondence freeze: {p1} {p2} {p3}")
        guards[g] = {"sgbm": p1, "adapter": p2, "opencv_calls": p3}
        files.update({n: sha256(run / n) for n in corr_files(g)})
        inputs[g] = {"calibration": {"path": str(SP.calibration_path(g)), "sha256": sha256(SP.calibration_path(g))},
                     "rgb_observation": {"path": str(SP.rgb_path(g)), "sha256": sha256(SP.rgb_path(g))}}
        BG.load_product(run / f"correspondence/{g}/sgbm-correspondences.npz")
    fz = {"schema": "AB1d3-correspondence-freeze-v1", "truth": SP.TRUTH_DERIVED,
          "statement": "SGBM CORRESPONDENCE FREEZE: the three full-raster SGBM records, the raw-core adapter records and "
                       "the truth-stripped raw correspondence products, frozen before any geometry and before any oracle, "
                       "Position, Object Index or evaluation product is opened",
          "files": files, "inputs": inputs, "guards": guards,
          "sgbm_code": {n: sha256(REPO / n) for n in SP.SGBM_CODE},
          "adapter_code": {n: sha256(REPO / n) for n in SP.ADAPTER_CODE},
          "sgbm_config_sha256": SP.config_sha256(SP.SGBM), "adapter_config_sha256": SP.config_sha256(SP.ADAPTER),
          "code": code_state(), "frozen_utc": utc()}
    write_json(path, fz)
    print(f"{PREFIX} freeze-correspondence: {len(files)} files hashed; guards verified; truth reads 0")
    return fz


def verify_correspondence_freeze(run: Path) -> dict:
    fz = read_json(run / "correspondence/correspondence-freeze.json")
    want = {n for g in SP.GAZES for n in corr_files(g)}
    bad = [n for n, h in fz["files"].items() if sha256(run / n) != h]
    if bad or set(fz["files"]) != want:
        raise SystemExit(f"{PREFIX} STOP the SGBM correspondence freeze does not verify: {bad}")
    return fz


# ------------------------------------------------------------------ spherical geometry (section 11; accepted, unchanged)
def spherical(run: Path) -> dict:
    once(run / "spherical" / SP.GAZES[0] / "epipolar-result.npz", "the spherical geometry")
    need(run / "correspondence/correspondence-freeze.json", "freeze-correspondence")
    verify_sources()
    verify_correspondence_freeze(run)
    out = {}
    for g in SP.GAZES:
        summ = AD.run_spherical_gaze(SP.calibration_path(g), run / f"correspondence/{g}/sgbm-correspondences.npz",
                                     run / "spherical" / g, run / "correspondence/correspondence-freeze.json")
        rec = read_json(run / "spherical" / g / "spherical-opened-files.json")
        own = SP.truth_reads(rec["events"])
        if rec["violations"] or any(rec["modules_loaded"].values()) or any(own.values()) or any(
                rec[k] for k in ("position_reads", "object_index_reads", "oracle_reads", "evaluation_reads")):
            raise SystemExit(f"{PREFIX} STOP {g} spherical guard: {rec['violations']}; modules {rec['modules_loaded']}")
        k, dd = summ["counts"], summ["distributions"]
        print(f"{PREFIX} spherical {g}: triangulated {k['triangulated_epipolar']:,}/{k['correspondences']:,}; |phi res| "
              f"max {dd['abs_phi_residual_rad']['max']:.2e}; truth reads 0; no cv2, no matcher")
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
    reads = ([run / "correspondence/correspondence-freeze.json"]
             + [run / n for g in SP.GAZES for n in corr_files(g) + geom_files(g)]
             + [SP.calibration_path(g) for g in SP.GAZES])
    with OpenGuard("ab1d3-freeze-geometry", reads, [run / "freeze"]) as gd:
        cfz = verify_correspondence_freeze(run)
        pre, files = {}, {}
        for g in SP.GAZES:
            prod = run / f"correspondence/{g}/sgbm-correspondences.npz"
            want = {str(SP.calibration_path(g).resolve()), str(prod.resolve())}
            sr = read_json(run / f"spherical/{g}/spherical-opened-files.json")
            ss = read_json(run / f"spherical/{g}/spherical-summary.json")
            p = {"spherical_reads_exactly_two": set(sr["data_reads"]) == want,
                 "violations_0": not sr["violations"],
                 "truth_reads_0": not any(SP.truth_reads(sr["events"]).values()),
                 "no_cv2_no_matcher_no_planar": not any(sr["modules_loaded"].values()),
                 "frozen_product": ss["inputs"]["correspondences"]["sha256"]
                 == cfz["files"][f"correspondence/{g}/sgbm-correspondences.npz"],
                 "same_calibration": ss["inputs"]["calibration"]["sha256"] == cfz["inputs"][g]["calibration"]["sha256"]}
            if not all(p.values()):
                raise SystemExit(f"{PREFIX} STOP {g} geometry freeze preconditions: {p}")
            pre[g] = p
            files.update({n: sha256(run / n) for n in [f"correspondence/{g}/sgbm-correspondences.npz"] + geom_files(g)})
        fz = {"schema": "AB1d3-geometry-freeze-v1", "truth": SP.TRUTH_DERIVED,
              "statement": "GEOMETRY FREEZE: the accepted AB1b spherical reconstruction of the SGBM raw correspondence "
                           "of all three gazes, frozen before any oracle, Position or evaluation product is opened",
              "files": files, "calibrations": {g: {"path": str(SP.calibration_path(g)),
                                                   "sha256": sha256(SP.calibration_path(g))} for g in SP.GAZES},
              "correspondence_freeze_sha256": sha256(run / "correspondence/correspondence-freeze.json"),
              "spherical_code": {n: sha256(REPO / n) for n in SP.SPHERICAL_CODE},
              "spherical_config_sha256": BG.SP.config_sha256(BG.SP.GEOMETRY), "preconditions": pre,
              "code": code_state(), "frozen_utc": utc()}
        write_json(path, fz)
    rec = gd.record()
    rec["truth_firewall_violations"] = len(rec["violations"])
    rec.update(SP.truth_reads(rec["events"]))
    write_json(run / "freeze/geometry-freeze-opened-files.json", rec)
    print(f"{PREFIX} freeze-geometry: {len(files)} files hashed; spherical read exactly the calibration and the frozen "
          f"SGBM product; truth reads 0")
    return fz


def verify_geometry_freeze(run: Path) -> dict:
    fz = read_json(run / "freeze/geometry-freeze.json")
    want = {n for g in SP.GAZES for n in [f"correspondence/{g}/sgbm-correspondences.npz"] + geom_files(g)}
    bad = [n for n, h in fz["files"].items() if sha256(run / n) != h]
    bad += [g for g, v in fz["calibrations"].items() if sha256(v["path"]) != v["sha256"]]
    if bad or set(fz["files"]) != want:
        raise SystemExit(f"{PREFIX} STOP the frozen geometry does not verify: {bad}")
    return fz


# ------------------------------------------------------------------ evaluation (sections 12-16; post-freeze)
def qd(a, mask=None) -> dict | None:
    a = np.asarray(a, np.float64)
    if mask is not None:
        a = a[np.asarray(mask, bool)]
    a = a[np.isfinite(a)].ravel()
    if a.size == 0:
        return None
    return {k: float(np.quantile(a, v)) for k, v in SP.QUANTILES.items()} | {"count": int(a.size)}


def ratio(num: int, den: int) -> float | None:
    return float(num / den) if den else None


def serviceable(c: dict, sg: dict, uv_l: np.ndarray, uv_r: np.ndarray) -> dict:
    """Section 12B: the oracle pair inside the frozen SGBM operating domain, through the accepted planar geometry."""
    import ab1c_planar as CP
    import ab1d3_sgbm as SG
    import fsg_stereo as FS
    w, h = c["image_size_wh"]
    kl, kr = (np.asarray(e["K"], np.float64) for e in c["eyes"])
    r = FS.rectification(c)
    same = all(np.array_equal(np.asarray(r[k]), sg[k]) for k in ("R1", "R2", "P1", "P2", "Q_full"))
    sup_l, sup_r = FS.support_mask(c, r, "L"), FS.support_mask(c, r, "R")
    gx, gy, gw, gh = (int(a) for a in sg["valid_disparity_roi"])
    roi = np.zeros((h, w), bool)
    roi[gy:gy + gh, gx:gx + gw] = True
    nd = int(sg["num_disparities"])
    uvr_l, w_l = CP.to_rectified(kl, sg["R1"], sg["P1"], uv_l)
    uvr_r, w_r = CP.to_rectified(kr, sg["R2"], sg["P2"], uv_r)
    x0l, y0l, inl, _, _ = SG.footprint(uvr_l, w, h)
    x0r, y0r, inr, _, _ = SG.footprint(uvr_r, w, h)
    inl &= w_l > SP.Z_EPS
    inr &= w_r > SP.Z_EPS
    left = inl & SG.gather4(sup_l, x0l, y0l, inl).all(-1) & SG.gather4(roi, x0l, y0l, inl).all(-1)
    right = inr & SG.gather4(sup_r, x0r, y0r, inr).all(-1)
    d = uvr_l[:, 0] - uvr_r[:, 0]
    with np.errstate(invalid="ignore", divide="ignore"):
        disp = np.isfinite(d) & (d >= 0) & (d <= nd - 1)
        x = FG.reproject_q(np.asarray(sg["Q_full"], np.float64), uvr_l, d)
        z = x[:, 2]
        zr = np.isfinite(x).all(-1) & (z >= SP.SGBM["z_rect_m"][0]) & (z <= SP.SGBM["z_rect_m"][1])
    s = left & right & disp & zr
    return {"serviceable": s, "left": left, "right": right, "disparity": disp, "z_rect": zr, "d_oracle": d,
            "z_rect_oracle": z, "rectification_identical": same}


def line_geometry(c: dict, M) -> dict:
    """The AB1d matcher's calibration-only epipolar line of every left core pixel (ab1d_match.Context, written out)."""
    cam_l, cam_r = M.make_cams(c)
    rows, cols = np.mgrid[:SP.CORE_SIZE, :SP.CORE_SIZE]
    uv = np.stack([cols.ravel() + SP.CORE_ORIGIN, rows.ravel() + SP.CORE_ORIGIN], -1).astype(np.float64)
    d = FG.rays_h(c["eyes"][0], uv)
    th_l, ph_l = M.theta_phi(d[:, 0], d[:, 1], d[:, 2])
    line = M.search_line(cam_r, d[:, 0], d[:, 1], d[:, 2], th_l, ph_l)
    return {"cam_r": cam_r, "line": line, "ph_l": ph_l}


def components(mask2d: np.ndarray) -> dict:
    import cv2
    m = np.asarray(mask2d, np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    sizes = np.sort(stats[1:, cv2.CC_STAT_AREA])[::-1] if n > 1 else np.zeros(0, np.int64)
    tot = int(m.sum())
    return {"pixels": tot, "components": int(n - 1), "largest": int(sizes[0]) if sizes.size else 0,
            "fraction_in_components_ge_min": ratio(int(sizes[sizes >= SP.COMPONENT_MIN_PX].sum()), tot),
            "component_min_px": SP.COMPONENT_MIN_PX}


def evaluation_core(c: dict, sg: dict, ad: dict, geo: dict, ora: dict, perf: dict, pos_l: np.ndarray, prim: dict,
                    M) -> tuple[dict, dict]:
    import cv2
    n = SP.CORE_SIZE ** 2
    oi = np.asarray(ora["left_core_row"], np.int64) * SP.CORE_SIZE + np.asarray(ora["left_core_col"], np.int64)
    O = np.zeros(n, bool)
    O[oi] = True
    V = np.asarray(ad["valid_adapter"], bool)
    gi = np.asarray(geo["left_core_row"], np.int64) * SP.CORE_SIZE + np.asarray(geo["left_core_col"], np.int64)
    if not np.array_equal(np.nonzero(V)[0], gi):
        raise SystemExit(f"{PREFIX} STOP the spherical result is not the adapter's product in core order")
    uv_or = np.full((n, 2), np.nan)
    uv_or[oi] = ora["uv_R"]
    uv_l_core = np.asarray(ad["uv_L"], np.float64)
    if not np.array_equal(uv_l_core[oi], np.asarray(ora["uv_L"], np.float64)):
        raise SystemExit(f"{PREFIX} STOP the oracle uv_L is not the raw left pixel centre")
    sv = serviceable(c, sg, uv_l_core[oi], ora["uv_R"])
    S = np.zeros(n, bool)
    S[oi] = sv["serviceable"]
    E = O & V
    ES = E & S
    e_idx = np.nonzero(E)[0]
    th_or = BG.theta_phi(FG.rays_h(c["eyes"][1], uv_or[e_idx]))[0]
    th_full = np.full(n, np.nan)
    th_full[gi] = geo["theta_R"]
    th_sg = th_full[e_idx]
    e_th = th_sg - th_or
    lg = line_geometry(c, M)
    ph_l = lg["ph_l"][e_idx]
    qu, qv, _ = M.project(lg["cam_r"], *M.direction(th_or, ph_l))
    q_oc = np.stack([qu, qv], -1)
    q_inf, t = lg["line"]["q_inf"][e_idx], lg["line"]["t"][e_idx]
    s_oc = np.sum((q_oc - q_inf) * t, -1)
    perp = np.abs((q_oc - q_inf)[:, 0] * (-t[:, 1]) + (q_oc - q_inf)[:, 1] * t[:, 0])

    def line_theta(s):
        uv = q_inf + np.asarray(s, np.float64)[..., None] * t
        return M.theta_phi(*M.rays(lg["cam_r"], uv[..., 0], uv[..., 1]))[0]
    scale = line_theta(s_oc + 0.5) - line_theta(s_oc - 0.5)
    e_px = e_th / scale
    e_f = lg["cam_r"].f * e_th
    # metric consequence
    p_sg_full = np.full((n, 3), np.nan)
    p_sg_full[gi] = geo["P_epi"]
    pi = np.asarray(perf["left_core_row"], np.int64) * SP.CORE_SIZE + np.asarray(perf["left_core_col"], np.int64)
    p_perf_full = np.full((n, 3), np.nan)
    p_perf_full[pi] = perf["P_epi"]
    p_sg, p_perf = p_sg_full[e_idx], p_perf_full[e_idx]
    rows, cols = e_idx // SP.CORE_SIZE + SP.CORE_ORIGIN, e_idx % SP.CORE_SIZE + SP.CORE_ORIGIN
    p_ref = FG.world_to_head(c, np.asarray(pos_l)[rows, cols].astype(np.float64))
    o_l = np.asarray(c["eyes"][0]["centre_h_m"], np.float64)
    n_o, n_e, n_s = int(O.sum()), int(E.sum()), int(S.sum())
    in_s = S[e_idx]
    metric, arrs = {}, {}
    for name, p_b in (("vs_perfect", p_perf), ("vs_position", p_ref)):
        e3 = np.linalg.norm(p_sg - p_b, axis=-1)
        rb = np.linalg.norm(p_b - o_l, axis=-1)
        rad = np.linalg.norm(p_sg - o_l, axis=-1) - rb
        within = {f"{tau:g}": {"count": int((e3 <= tau).sum()), "precision": ratio(int((e3 <= tau).sum()), n_e),
                               "effective_oracle_coverage": ratio(int((e3 <= tau).sum()), n_o),
                               "effective_serviceable_coverage": ratio(int(((e3 <= tau) & in_s).sum()), n_s)}
                  for tau in SP.METRIC_FRACTIONS_M}
        metric[name] = {"pairs": int(e3.size), "error_3d_m": qd(e3), "radial_signed_m": qd(rad),
                        "range_relative": qd(np.abs(rad) / rb), "within_m": within}
        arrs[f"error_3d_{name}_m"] = e3
        arrs[f"radial_signed_{name}_m"] = rad
    ae = np.abs(e_px)
    px_within = {f"{b:g}": {"count": int((ae <= b).sum()), "precision": ratio(int((ae <= b).sum()), n_e),
                            "effective_oracle_coverage": ratio(int((ae <= b).sum()), n_o),
                            "effective_serviceable_coverage": ratio(int(((ae <= b) & in_s).sum()), n_s)}
                 for b in SP.PX_BINS}
    cat = {f">{b:g}px": {"count": int((ae > b).sum()), "fraction_of_evaluable": ratio(int((ae > b).sum()), n_e),
                         "fraction_of_oracle": ratio(int((ae > b).sum()), n_o)} for b in SP.CATASTROPHIC_PX}
    # comparison with the accepted AB1d2 primitive matcher (same oracle pixels)
    p_idx = np.asarray(prim["core_index"], np.int64)
    p_epx = np.full(n, np.nan)
    p_epx[p_idx] = prim["e_px"]
    p_e3 = np.full(n, np.nan)
    p_e3[p_idx] = prim["error_3d_vs_perfect_m"]
    cls = np.asarray(prim["class_map"])
    p_valid = (cls == 0) | (cls == 2)
    s_epx = np.full(n, np.nan)
    s_epx[e_idx] = e_px
    s_e3 = np.full(n, np.nan)
    s_e3[e_idx] = arrs["error_3d_vs_perfect_m"]
    p_eval = np.zeros(n, bool)
    p_eval[p_idx] = True
    with np.errstate(invalid="ignore"):
        good_p = p_eval & (np.abs(p_epx) <= SP.GOOD_PX)
        good_s = E & (np.abs(s_epx) <= SP.GOOD_PX)
    catmap = np.full(n, -1, np.int8)
    for k, m in enumerate((good_p & good_s, good_p & ~good_s, ~good_p & good_s, ~good_p & ~good_s)):
        catmap[O & m] = k
    both_eval = E & p_eval

    def side(valid_count, ev_mask, epx, e3):
        a = np.abs(epx[ev_mask])
        ee = e3[ev_mask]
        ne = int(ev_mask.sum())
        return {"valid_count": int(valid_count), "evaluable": ne, "oracle_coverage": ratio(ne, n_o),
                "median_px": float(np.median(a)) if ne else None,
                "within_px_precision": {f"{b:g}": ratio(int((a <= b).sum()), ne) for b in SP.PX_BINS},
                "within_px_effective_oracle_coverage": {f"{b:g}": ratio(int((a <= b).sum()), n_o) for b in SP.PX_BINS},
                "median_3d_m": float(np.median(ee)) if ne else None,
                "within_m_precision": {f"{t:g}": ratio(int((ee <= t).sum()), ne) for t in SP.METRIC_FRACTIONS_M},
                "within_m_effective_oracle_coverage": {f"{t:g}": ratio(int((ee <= t).sum()), n_o)
                                                       for t in SP.METRIC_FRACTIONS_M},
                "catastrophic_fraction_of_evaluable": {f">{b:g}px": ratio(int((a > b).sum()), ne)
                                                       for b in SP.CATASTROPHIC_PX}}
    comparison = {
        "primitive_ab1d2": side(p_valid.sum(), p_eval, p_epx, p_e3),
        "sgbm": side(V.sum(), E, s_epx, s_e3),
        "categories_on_full_oracle": {name: {"count": int((catmap == k).sum()), "fraction": ratio(int((catmap == k).sum()),
                                                                                                n_o)}
                                      for k, name in enumerate(SP.CATEGORIES)},
        "common_evaluable": {"count": int(both_eval.sum()),
                             "median_px_primitive": float(np.median(np.abs(p_epx[both_eval]))) if both_eval.any() else None,
                             "median_px_sgbm": float(np.median(np.abs(s_epx[both_eval]))) if both_eval.any() else None,
                             "within_1px_primitive": ratio(int((np.abs(p_epx[both_eval]) <= 1).sum()), int(both_eval.sum())),
                             "within_1px_sgbm": ratio(int((np.abs(s_epx[both_eval]) <= 1).sum()), int(both_eval.sum()))},
        "category_definition": "correct = evaluable and |pixel-equivalent error| <= 1 px; invalid / unevaluable counts "
                               "as not correct; categories partition the full oracle set",
    }
    # spatial analysis (core 256 x 256)
    grid = lambda m: np.asarray(m, bool).reshape(SP.CORE_SIZE, SP.CORE_SIZE)  # noqa: E731
    cat10 = np.zeros(n, bool)
    cat10[e_idx[ae > SP.CATASTROPHIC_PX[0]]] = True
    cat100 = np.zeros(n, bool)
    cat100[e_idx[ae > SP.CATASTROPHIC_PX[1]]] = True
    invalid_near = cv2.dilate((~V).reshape(SP.CORE_SIZE, SP.CORE_SIZE).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    spatial = {"sgbm_valid": components(grid(V)), "catastrophic_gt10px": components(grid(cat10)),
               "catastrophic_gt100px": components(grid(cat100)),
               "catastrophic_gt10px_within_2px_of_invalid": ratio(int((grid(cat10) & invalid_near).sum()), int(cat10.sum())),
               "evaluable_within_2px_of_invalid": ratio(int((grid(E) & invalid_near).sum()), n_e)}
    # attrition (adapter stages) and reference sets
    counts = {"raw_core": n, "full_oracle": n_o, "serviceable_oracle": n_s, "sgbm_valid": int(V.sum()),
              "sgbm_valid_and_oracle": n_e, "sgbm_valid_and_serviceable": int(ES.sum()),
              "sgbm_valid_non_oracle": int((V & ~O).sum()), "sgbm_valid_oracle_non_serviceable": int((E & ~S).sum()),
              "serviceable_coverage": ratio(int(ES.sum()), n_s), "full_oracle_coverage": ratio(n_e, n_o),
              "serviceable_fraction_of_oracle": ratio(n_s, n_o),
              "serviceable_terms_on_oracle": {k: int(sv[k].sum()) for k in ("left", "right", "disparity", "z_rect")}}
    pp = np.asarray(ad["planar_q_point_secondary"], np.float64)[gi]
    secondary = {"statement": "SECONDARY diagnostic only: SGBM's own planar Q reconstruction of the same adapted "
                              "correspondence vs the accepted spherical reconstruction (truth-free consistency); never "
                              "the primary metric",
                 "planar_q_vs_spherical_m": qd(np.linalg.norm(pp - np.asarray(geo["P_epi"]), axis=-1))}
    summ = {"counts": counts,
            "primary": {"e_theta_signed_rad": qd(e_th), "e_theta_abs_rad": qd(np.abs(e_th)),
                        "px_equivalent_signed": qd(e_px), "px_equivalent_abs": qd(ae), "px_within": px_within,
                        "catastrophic": cat, "focal_approximation_abs_px": qd(np.abs(e_f)),
                        "local_scale_rad_per_px": qd(scale), "oracle_on_curve_perpendicular_px": qd(perp),
                        "serviceable_only": {"px_equivalent_abs": qd(ae, in_s)}},
            "metric": metric, "comparison_ab1d2": comparison, "spatial": spatial, "secondary": secondary,
            "sgbm_distributions_product": {
                "refined_disparity_px": qd(ad["disparity_bilinear_px"], V),
                "raw_fixed_point_disparity_x16": qd(np.asarray(ad["disparity_sgbm_bilinear_px"]) * 16.0, V),
                "refinement_delta_px": qd(ad["refinement_delta_bilinear_px"], V),
                "lr_residual_px": qd(ad["lr_residual_bilinear_px"], V)}}
    arrs.update({"core_index": e_idx.astype(np.int32), "theta_R_oracle": th_or, "theta_R_sgbm": th_sg, "e_theta": e_th,
                 "s_oracle_on_curve": s_oc, "oracle_perpendicular_px": perp, "local_scale_rad_per_px": scale,
                 "e_px": e_px, "e_focal_px": e_f, "P_sgbm": p_sg, "P_perfect": p_perf, "P_reference": p_ref,
                 "oracle_mask": O, "serviceable_mask": S, "sgbm_valid_mask": V, "category_map": catmap,
                 "primitive_e_px_core": p_epx, "primitive_e3_core": p_e3, "sgbm_e_px_core": s_epx, "sgbm_e3_core": s_e3,
                 "serviceable_left": sv["left"], "serviceable_right": sv["right"],
                 "serviceable_disparity": sv["disparity"], "serviceable_z_rect": sv["z_rect"],
                 "d_oracle_rect": sv["d_oracle"], "z_rect_oracle": sv["z_rect_oracle"]})
    if not sv["rectification_identical"]:
        raise SystemExit(f"{PREFIX} STOP the recomputed rectification differs from the frozen SGBM record")
    return summ, arrs


def pooled(arrs: list[dict], per: dict) -> dict:
    e = np.concatenate([np.abs(a["e_px"]) for a in arrs])
    e3 = np.concatenate([a["error_3d_vs_perfect_m"] for a in arrs])
    n_o = sum(per[g]["counts"]["full_oracle"] for g in SP.GAZES)
    return {"evaluable": int(e.size), "full_oracle": n_o, "px_equivalent_abs": qd(e),
            "px_within_precision": {f"{b:g}": ratio(int((e <= b).sum()), e.size) for b in SP.PX_BINS},
            "error_3d_vs_perfect_m": qd(e3),
            "within_m_precision": {f"{t:g}": ratio(int((e3 <= t).sum()), e3.size) for t in SP.METRIC_FRACTIONS_M},
            "within_m_effective_oracle_coverage": {f"{t:g}": ratio(int((e3 <= t).sum()), n_o)
                                                   for t in SP.METRIC_FRACTIONS_M}}


def evaluation_files() -> list[str]:
    return ["evaluation/evaluation-summary.json", "evaluation/evaluation-opened-files.json"] + [
        f"evaluation/{g}/evaluation-result.npz" for g in SP.GAZES]


def evaluate(run: Path) -> dict:
    out = run / "evaluation"
    once(out / "evaluation-summary.json", "the evaluation")
    need(run / "freeze/geometry-freeze.json", "freeze-geometry")
    out.mkdir(parents=True, exist_ok=True)
    import ab1d_match as M
    frozen = ([run / "freeze/geometry-freeze.json", run / "correspondence/correspondence-freeze.json"]
              + [run / n for g in SP.GAZES for n in corr_files(g) + geom_files(g)]
              + [SP.calibration_path(g) for g in SP.GAZES])
    refs = [p for g in SP.GAZES for p in bench_paths(g)] + [SP.a1d2(a1d2_eval_rel(g)) for g in SP.GAZES]
    with OpenGuard("ab1d3-evaluation", frozen + refs, [out]) as gd:
        verify_correspondence_freeze(run)
        verify_geometry_freeze(run)
        gd.mark("freezes_verified")
        data = {}
        for g in SP.GAZES:
            data[g] = (read_json(SP.calibration_path(g)), load_npz(run / f"sgbm/{g}/sgbm-record.npz"),
                       load_npz(run / f"correspondence/{g}/adapter-record.npz"),
                       load_npz(run / f"spherical/{g}/epipolar-result.npz"))
        gd.mark("reference_access_begins")
        bench, a1d2h = {}, {}
        for g in SP.GAZES:
            for p in bench_paths(g):
                rel = str(p.relative_to(SP.A1C_RUN))
                h = sha256(p)
                if h != bench_pins()[rel]:
                    raise SystemExit(f"{PREFIX} STOP benchmark file changed: {rel}")
                bench[rel] = h
            rel = a1d2_eval_rel(g)
            h = sha256(SP.a1d2(rel))
            if h != SP.A1D2_PINS[rel]:
                raise SystemExit(f"{PREFIX} STOP accepted AB1d2 evaluation changed: {rel}")
            a1d2h[rel] = h
        import ab1d_spec as DS
        per, arrs = {}, []
        for g in SP.GAZES:
            c, sg, ad, geo = data[g]
            ora, perf = load_npz(DS.oracle_path(g)), load_npz(DS.perfect_path(g))
            with np.load(DS.reference_path(g), allow_pickle=False) as z:
                pos_l = np.asarray(z["position_w_L"])
            prim = load_npz(SP.a1d2(a1d2_eval_rel(g)))
            summ, arr = evaluation_core(c, sg, ad, geo, ora, perf, pos_l, prim, M)
            (out / g).mkdir(parents=True, exist_ok=True)
            np.savez_compressed(out / g / "evaluation-result.npz", **arr)
            summ["attrition"] = read_json(run / f"correspondence/{g}/adapter-summary.json")["attrition"]
            per[g] = summ
            arrs.append(arr)
            k, p, m = summ["counts"], summ["primary"], summ["metric"]["vs_perfect"]
            print(f"{PREFIX} evaluate {g}: oracle {k['full_oracle']:,}, serviceable {k['serviceable_oracle']:,}, SGBM valid "
                  f"{k['sgbm_valid']:,}, evaluable {k['sgbm_valid_and_oracle']:,} (coverage {k['full_oracle_coverage']:.3f}, "
                  f"serviceable {k['serviceable_coverage']:.3f}); |px| median {p['px_equivalent_abs']['median']:.3f} "
                  f"p95 {p['px_equivalent_abs']['p95']:.2f}; <=1 px {p['px_within']['1']['precision']:.3f}; 3-D median "
                  f"{m['error_3d_m']['median'] * 1e3:.1f} mm; <=12 mm precision {m['within_m']['0.012']['precision']:.3f} / "
                  f"effective {m['within_m']['0.012']['effective_oracle_coverage']:.3f}")
        summary = {"schema": "AB1d3-evaluation-summary-v1", "truth": SP.TRUTH_REFERENCE,
                   "statement": "REFERENCE / EVALUATION: after both freezes, the SGBM raw correspondence is scored against "
                                "the accepted AB1c perfect correspondence (benchmark only), its spherical reconstruction "
                                "against the AB1c perfect reconstruction and Blender Position, and compared on the same "
                                "oracle pixels with the accepted AB1d2 primitive matcher; descriptive only; no "
                                "acceptance threshold",
                   "benchmark_files": bench, "ab1d2_evaluation_files": a1d2h, "per_gaze": per,
                   "pooled": pooled(arrs, per),
                   "constants": {"good_px": SP.GOOD_PX, "px_bins": list(SP.PX_BINS),
                                 "catastrophic_px": list(SP.CATASTROPHIC_PX),
                                 "metric_fractions_m": list(SP.METRIC_FRACTIONS_M), "quantiles": SP.QUANTILES,
                                 "serviceable": SP.SERVICEABLE, "component_min_px": SP.COMPONENT_MIN_PX},
                   "code": code_state()}
        write_json(out / "evaluation-summary.json", summary)
    rec = gd.record()
    rec["truth_firewall_violations"] = len(rec["violations"])
    write_json(out / "evaluation-opened-files.json", rec)
    if rec["violations"]:
        raise SystemExit(f"{PREFIX} STOP evaluation guard: {rec['violations'][:3]}")
    return summary


# ------------------------------------------------------------------ manifest / CLI
def write_manifest(run: Path) -> dict:
    files = sorted(str(p.relative_to(run)) for p in run.rglob("*") if p.is_file()
                   and p.name not in ("manifest.json", "check-summary.json", "process-log.jsonl"))
    m = {"schema": "AB1d3-manifest-v1", "experiment": SP.EXPERIMENT, "contract": SP.CONTRACT, "code": code_state(),
         "base_commit": SP.BASE_COMMIT, "a1d2_run": str(SP.A1D2_RUN), "a1c_run": str(SP.A1C_RUN), "truth": TRUTH_CLASSES,
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
        if a.cmd == "preflight":
            ok = preflight(run)["passed"]
            status = "ok" if ok else "failed"
            return 0 if ok else 1
        if a.cmd in SP.CANONICAL:
            require_committed(a.cmd)
        {"source": source, "sgbm": sgbm, "raw-core-adapter": raw_core_adapter,
         "freeze-correspondence": freeze_correspondence, "spherical": spherical, "freeze-geometry": freeze_geometry,
         "evaluate": evaluate}.get(a.cmd, lambda r: None)(run)
        if a.cmd == "visualize":
            import ab1d3_visuals
            ab1d3_visuals.visualize(run, a.visuals.resolve())
            write_manifest(run)
        status = "ok"
        return 0
    finally:
        log_process(run, a.cmd, t0, status)


if __name__ == "__main__":
    raise SystemExit(main())
