"""Active Bootstrap-1a: the first natural stereo look (run order and truth boundary).

Contract: docs/active-bootstrap/ab1a-first-natural-stereo-look-contract.md.

    .venv/bin/python tools/active_bootstrap/ab1a_run.py synthetic --run RUN
    .venv/bin/python tools/active_bootstrap/ab1a_run.py rehearse  --run RUN
    .venv/bin/python tools/active_bootstrap/ab1a_run.py prelook   --run RUN
    .venv/bin/python tools/active_bootstrap/ab1a_run.py preflight --run RUN
    .venv/bin/python tools/active_bootstrap/ab1a_run.py acquire   --run RUN
    .venv/bin/python tools/active_bootstrap/ab1a_run.py measure   --run RUN
    .venv/bin/python tools/active_bootstrap/ab1a_run.py freeze    --run RUN
    .venv/bin/python tools/active_bootstrap/ab1a_run.py evaluate  --run RUN
    .venv/bin/python tools/active_bootstrap/ab1a_run.py visualize --run RUN --visuals VIS

Exactly one gaze is executed: the frozen NB1c RGB gaze #1, once.  ``measure`` reads only the calibration and the
RGB observation under the accepted ``nb1a_guard.OpenGuard``; ``evaluate`` opens evaluation-only truth only after the
measurement freeze verifies.  No controller, no surface map, no fusion, no FSG6f, no second gaze.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "natural_bootstrap"))

import ab1a_spec as SP  # noqa: E402
import ab1a_stereo as ST  # noqa: E402
import fsg_geometry as FG  # noqa: E402  (accepted, read-only)
import fsg_stereo as FS  # noqa: E402  (accepted, read-only)
from nb1a_guard import OpenGuard  # noqa: E402  (accepted, read-only)

PREFIX = "[ab1a]"
RENDER_SCRIPT = HERE / "ab1a_render.py"


# ------------------------------------------------------------------ utilities
sha256 = ST.sha256
write_json = ST.write_json


def read_json(path):
    return json.loads(Path(path).read_text())


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


def log_process(run: Path, command: str, t0: float, status: str, extra: dict | None = None) -> None:
    run.mkdir(parents=True, exist_ok=True)
    entry = {"command": command, "argv": sys.argv, "executable": sys.executable, "code": code_state(),
             "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
             "seconds": round(time.time() - t0, 3), "status": status, **(extra or {})}
    with open(run / "process-log.jsonl", "a") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")


def require_committed(what: str) -> dict:
    cs = code_state()
    if cs["dirty"] or not cs["pushed"]:
        raise SystemExit(f"{PREFIX} STOP {what} runs only from a clean, pushed implementation commit: {cs}")
    return cs


def blender(run: Path, mode: str, blend: Path | None, log: Path) -> dict:
    argv = [SP.BLENDER, "-b"] + ([str(blend)] if blend else ["--factory-startup"]) + [
        "--python-exit-code", "1", "-P", str(RENDER_SCRIPT), "--", "--mode", mode, "--run", str(run),
        "--head-pose", str(SP.HEAD_POSE_SOURCE[0])]
    t0 = time.time()
    proc = subprocess.run(argv, cwd=REPO, capture_output=True, text=True)
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(proc.stdout + proc.stderr)
    ok = proc.returncode == 0 and f"[ab1a-render] COMPLETE {mode}" in proc.stdout
    return {"blender": {"mode": mode, "argv": argv, "returncode": proc.returncode, "seconds": round(time.time() - t0, 3),
                        "complete_marker": ok, "log": str(log)}}


# ------------------------------------------------------------------ the frozen action (section 3)
def verify_action() -> dict:
    fz_path, fz_sha = SP.NB1C_FREEZE
    cg_path, cg_sha = SP.NB1C_CANDIDATES
    mf_path, mf_sha = SP.NB1C_MANIFEST
    got = {"freeze": sha256(fz_path), "candidates": sha256(cg_path), "manifest": sha256(mf_path)}
    if got != {"freeze": fz_sha, "candidates": cg_sha, "manifest": mf_sha}:
        raise SystemExit(f"{PREFIX} STOP accepted NB1c action identity mismatch: {got}")
    fz, mf = read_json(fz_path), read_json(mf_path)
    sel = fz_path.parent
    bad = [n for n, h in fz["files"].items() if sha256(sel / n) != h]
    if bad or fz["files"].get("candidate-gazes.json") != cg_sha or mf["files"].get("selection/candidate-gazes.json") != cg_sha:
        raise SystemExit(f"{PREFIX} STOP NB1c freeze / manifest do not pin candidate-gazes.json: {bad}")
    g = read_json(cg_path)["gazes"][0]
    want = {"rank": SP.GAZE_RANK, "row": SP.GAZE_ROW, "col": SP.GAZE_COL, "yaw_deg": SP.GAZE_YAW_DEG,
            "pitch_deg": SP.GAZE_PITCH_DEG}
    if {k: g[k] for k in want} != want or fz["gazes"][0] != {"rank": 1, "row": SP.GAZE_ROW, "col": SP.GAZE_COL}:
        raise SystemExit(f"{PREFIX} STOP rank 1 is not the declared gaze: {g}")
    if SP.gaze_cell_centre(g["row"], g["col"]) != (g["yaw_deg"], g["pitch_deg"]):
        raise SystemExit(f"{PREFIX} STOP rank 1 is not its cell centre")
    return g


def planned_calibration() -> dict:
    pose = read_json(SP.HEAD_POSE_SOURCE[0])
    if sha256(SP.HEAD_POSE_SOURCE[0]) != SP.HEAD_POSE_SOURCE[1]:
        raise SystemExit(f"{PREFIX} STOP accepted head-pose record changed")
    try:
        return FG.make_calibration(SP.PROFILE, SP.GAZE_YAW_DEG, SP.GAZE_PITCH_DEG, SP.VERGENCE_M, ipd=SP.IPD_M,
                                   head_r_wh=np.asarray(pose["head_R_wh"]),
                                   head_origin_w=np.asarray(pose["head_origin_w_m"]), tangent_frame=SP.TANGENT_FRAME)
    except ValueError as exc:
        raise SystemExit(f"{PREFIX} STOP gaze #1 cannot be represented by baseline_projected geometry: {exc}")


def prelook(run: Path) -> dict:
    src, pre = run / "source", run / "prelook"
    if (pre / "prelook-geometry.json").exists():
        raise SystemExit(f"{PREFIX} STOP the pre-look record exists; it is written once, before acquisition")
    ST.verify_inherited()
    g = verify_action()
    src.mkdir(parents=True, exist_ok=True)
    pre.mkdir(parents=True, exist_ok=True)
    write_json(src / "nb1c-action-manifest.json", {
        "schema": "AB1a-nb1c-action-manifest-v1", "truth": SP.TRUTH_DERIVED, "action_source": SP.ACTION_SOURCE,
        "statement": "the first frozen NB1c RGB candidate gaze, consumed verbatim; no recomputation, no movement, no "
                     "snapping; gazes 2-6 are not executed",
        "nb1c_freeze": {"path": str(SP.NB1C_FREEZE[0]), "sha256": SP.NB1C_FREEZE[1]},
        "nb1c_candidate_gazes": {"path": str(SP.NB1C_CANDIDATES[0]), "sha256": SP.NB1C_CANDIDATES[1]},
        "nb1c_manifest": {"path": str(SP.NB1C_MANIFEST[0]), "sha256": SP.NB1C_MANIFEST[1]},
        "gaze": g, "cell_centre_convention": "yaw = -180 + 0.5 (col + 0.5), pitch = 90 - 0.5 (row + 0.5)",
        "head_pose_source": {"path": str(SP.HEAD_POSE_SOURCE[0]), "sha256": SP.HEAD_POSE_SOURCE[1]}})
    c = planned_calibration()
    try:
        geo = ST.prelook_geometry(c)
    except ValueError as exc:
        raise SystemExit(f"{PREFIX} STOP the accepted rectification refuses gaze #1: {exc}")
    write_json(pre / "planned-calibration.json", c)
    geo["planned_calibration_sha256"] = sha256(pre / "planned-calibration.json")
    write_json(pre / "prelook-geometry.json", geo)
    e = geo["eyes"]["L"]
    print(f"{PREFIX} prelook: gaze ({g['yaw_deg']:+.2f}, {g['pitch_deg']:+.2f}); L = {geo['L']:.10f}; "
          f"B_perp = {geo['B_perp_m'] * 1000:.3f} mm; rectified core centre {e['rectified_core_centre_from_gaze_deg']:.3f} "
          f"deg from the gaze, {e['rectified_core_centre_from_baseline_deg']:.3f} deg from the baseline")
    return geo


def preflight(run: Path) -> dict:
    if sha256(REPO / SP.BLEND) != SP.BLEND_SHA256:
        raise SystemExit(f"{PREFIX} STOP Classroom blend changed")
    res = blender(run, "preflight", REPO / SP.BLEND, run / "logs/preflight-blender.log")
    if not res["blender"]["complete_marker"]:
        raise SystemExit(f"{PREFIX} STOP preflight failed; see {res['blender']['log']}")
    pf = read_json(run / "preflight/preflight.json")
    print(f"{PREFIX} preflight: no render; device {pf['device']}; EYE pose diff {pf['eye_pose']['max_abs_diff_from_accepted']}; "
          f"calibration diff {pf['calibration_max_abs_diff_from_planned']}")
    return res


def acquire(run: Path) -> dict:
    require_committed("acquire")
    for d in (run / "acquisition", run / "evaluation_only"):
        if d.exists() and any(d.iterdir()):
            raise SystemExit(f"{PREFIX} STOP {d} exists: the canonical gaze is rendered once")
    if not (run / "prelook/prelook-geometry.json").is_file() or not (run / "preflight/preflight.json").is_file():
        raise SystemExit(f"{PREFIX} STOP prelook and preflight come first")
    verify_action()
    if sha256(REPO / SP.BLEND) != SP.BLEND_SHA256:
        raise SystemExit(f"{PREFIX} STOP Classroom blend changed")
    res = blender(run, "canonical", REPO / SP.BLEND, run / "logs/acquire-blender.log")
    if not res["blender"]["complete_marker"]:
        print(f"{PREFIX} STOP the canonical acquisition failed; see {res['blender']['log']}. It is NOT retried: a second "
              f"acquisition is a decision for Luiz and Chat.")
        return res
    acq = run / "acquisition"
    with np.load(acq / "rgb-observation.npz") as z:
        names = sorted(z.files)
    a = read_json(acq / "acquisition.json")
    diff = _calib_diff(read_json(run / "prelook/planned-calibration.json"), read_json(acq / "calibration.json"))
    problems = []
    if names != sorted(SP.RGB_KEYS):
        problems.append(f"rgb observation arrays {names}")
    if not diff <= SP.CALIBRATION_TOL:
        problems.append(f"calibration differs from planned by {diff}")
    if (a["device"], a["spp"], a["render_seeds_lr"]) != (SP.DEVICE, SP.SPP, SP.SEEDS):
        problems.append(f"settings {a['device']} {a['spp']} {a['render_seeds_lr']}")
    if a["rgb_observation_sha256"] != sha256(acq / "rgb-observation.npz"):
        problems.append("rgb observation hash")
    if problems:
        raise SystemExit(f"{PREFIX} STOP acquisition verification: {problems}")
    print(f"{PREFIX} acquire: gaze {a['gaze_yaw_pitch_deg']}; {a['device']} {a['spp']} spp; seeds {a['render_seeds_lr']}; "
          f"render seconds {a['render_seconds_lr']}; rgb observation {a['rgb_observation_sha256'][:12]}")
    return res


def _calib_diff(a, b) -> float:
    if isinstance(a, dict) and isinstance(b, dict):
        return max([_calib_diff(a[k], b[k]) for k in a] or [0.0]) if set(a) == set(b) else math.inf
    if isinstance(a, list) and isinstance(b, list):
        return max([_calib_diff(x, y) for x, y in zip(a, b)] or [0.0]) if len(a) == len(b) else math.inf
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        return abs(float(a) - float(b))
    return 0.0 if a == b else math.inf


# ------------------------------------------------------------------ measurement and freeze (sections 7-8)
def measure(run: Path) -> dict:
    out = run / "measurement"
    if (out / "stereo-result.npz").exists():
        raise SystemExit(f"{PREFIX} STOP the natural measurement exists; it is made once")
    ST.verify_inherited()
    summ, rec = ST.measure_dir(run / "acquisition", out)
    if rec["violations"]:
        raise SystemExit(f"{PREFIX} STOP measurement truth-firewall violations: {rec['violations']}")
    d, r = summ["disparity_px_valid"], summ["range_left_m_valid"]
    print(f"{PREFIX} measure: valid {summ['valid_count']}/{summ['core_pixels']} ({summ['valid_fraction_core']:.6f}); "
          f"disparity median {d['median'] if d else None}; range median {r['median'] if r else None}; data reads "
          f"{len(rec['data_reads'])}; violations 0 ({summ['seconds']} s)")
    return summ


def freeze_files(run: Path) -> dict:
    return {n: sha256(run / n) for n in SP.FROZEN_MEASUREMENT}


def freeze(run: Path) -> dict:
    path = run / "measurement/measurement-freeze.json"
    if path.exists():
        raise SystemExit(f"{PREFIX} STOP the measurement freeze exists")
    opened = read_json(run / "measurement/measurement-opened-files.json")
    if opened["violations"]:
        raise SystemExit(f"{PREFIX} STOP measurement violations")
    rec = {"schema": "AB1a-measurement-freeze-v1", "truth": SP.TRUTH_DERIVED,
           "statement": "the natural RGB-only measurement, frozen before any evaluation-only file is opened",
           "files": freeze_files(run),
           "nb1c_action_source": {"candidate-gazes.json": sha256(SP.NB1C_CANDIDATES[0]),
                                  "rgb-gaze-freeze.json": sha256(SP.NB1C_FREEZE[0])},
           "matcher_config": SP.MATCHER, "matcher_config_sha256": ST.config_sha256(),
           "matcher_code": {n: sha256(REPO / n) for n in SP.MATCHER_CODE},
           "truth_firewall_violations": len(opened["violations"]),
           "code": code_state(), "frozen_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    write_json(path, rec)
    print(f"{PREFIX} freeze: {len(rec['files'])} files hashed; violations {rec['truth_firewall_violations']}")
    return rec


def verify_measurement_freeze(run: Path) -> dict:
    fz = read_json(run / "measurement/measurement-freeze.json")
    bad = [n for n, h in fz["files"].items() if sha256(run / n) != h]
    if bad or set(fz["files"]) != set(SP.FROZEN_MEASUREMENT):
        raise SystemExit(f"{PREFIX} STOP the frozen measurement does not verify: {bad}")
    return fz


# ------------------------------------------------------------------ post-freeze reference / evaluation (section 9)
def _q(a, quantiles=None) -> dict | None:
    a = np.asarray(a, np.float64).ravel()
    a = a[np.isfinite(a)]
    if a.size == 0:
        return None
    return {k: float(np.quantile(a, q)) for k, q in (quantiles or SP.QUANTILES).items()} | {"count": int(a.size)}


def _errors(xyz_a, xyz_b, mask, c_l) -> dict:
    a, b = xyz_a[mask].astype(np.float64), xyz_b[mask].astype(np.float64)
    e3 = np.linalg.norm(a - b, axis=-1)
    signed = np.linalg.norm(a - c_l, axis=-1) - np.linalg.norm(b - c_l, axis=-1)
    return {"pixels": int(mask.sum()), "error_3d_m": _q(e3), "radial_abs_m": _q(np.abs(signed)),
            "radial_signed_m": _q(signed, {"min": 0.0, **SP.QUANTILES}),
            "fraction_3d_within_m": ({f"{t:.3f}": float((e3 <= t).mean()) for t in SP.ERROR_FRACTIONS_M}
                                     if e3.size else None)}


def camera_model(c: dict, pos_w: dict) -> dict:
    """Blender Position (first sample, inside the BOX pixel) projected through the calibration: |du|, |dv| <= 0.5."""
    w, h = c["image_size_wh"]
    out = {}
    for i, side in enumerate(("L", "R")):
        p = np.asarray(pos_w[side], np.float64)
        geom = np.any(p != 0, axis=-1)
        uv, z = FG.project_h(c["eyes"][i], FG.world_to_head(c, p))
        res = np.abs(uv - FG.pixels(w, h))
        m = geom & (z > 0)
        worst = float(res[m].max()) if m.any() else None
        out[side] = {"geometry_pixels": int(geom.sum()), "behind_camera": int((geom & ~(z > 0)).sum()),
                     "max_abs_residual_px": worst,
                     "beyond_tolerance": int((m & (res.max(axis=-1) > SP.CAMERA_MODEL_TOL_PX)).sum())}
    out["ok"] = all(out[s]["beyond_tolerance"] == 0 and out[s]["behind_camera"] == 0 for s in ("L", "R"))
    out["tolerance_px"] = SP.CAMERA_MODEL_TOL_PX
    return out


def evaluation_core(c: dict, nat: dict, rgb: dict, ref: dict, names: dict) -> tuple[dict, dict]:
    """The declared post-freeze descriptors (contract section 9)."""
    import cv2
    import classroom_oracle1_matcher as OM   # accepted local oracle, read-only, evaluation only
    obs = {**rgb, **ref}
    orec, ometa, _state = OM.compute(c, obs)
    r = FS.rectification(c)
    x, y, cw, ch = map(int, r["crop_xywh"])
    sl = np.s_[y:y + ch, x:x + cw]
    pos_l = FS.remap(np.asarray(ref["position_w_L"], np.float32), r, "L", cv2.INTER_NEAREST)[sl].astype(np.float64)
    geom = np.any(pos_l != 0, axis=-1)
    left_h = FG.world_to_head(c, pos_l)
    ids_l = orec["instance_id"]
    N, R = np.asarray(nat["valid"], bool), np.asarray(orec["valid"], bool)
    c_l = np.asarray(c["eyes"][0]["centre_h_m"], np.float64)
    xyz_n = np.asarray(nat["xyz_h"], np.float64)
    xyz_r = np.asarray(orec["xyz_h"], np.float64)
    overlap = N & R
    # composition of natural-valid pixels (left Object Index and left Position at the rectified pixel)
    cat = N & (ids_l > 0)
    o0 = N & (ids_l == 0) & geom
    nogeo = N & ~geom
    inst, cnt = np.unique(ids_l[cat], return_counts=True)
    composition = {"natural_valid": int(N.sum()), "catalog": int(cat.sum()), "O_0_noncatalog_geometry": int(o0.sum()),
                   "no_geometry": int(nogeo.sum()),
                   "instances": [{"instance_id": int(i), "object_name": names.get(int(i), ""), "pixels": int(k)}
                                 for k, i in sorted(zip(cnt.tolist(), inst.tolist()), key=lambda t: (-t[0], t[1]))],
                   "distinct_catalog_instances": int(len(inst))}
    # reasons for natural-only pixels (the oracle's own visibility rule, re-traced)
    uv = orec["right_reprojection_uv"].astype(np.float64)
    finite = np.isfinite(uv).all(axis=-1)
    inside = finite & (uv[..., 0] >= 0) & (uv[..., 0] <= cw - 1) & (uv[..., 1] >= 0) & (uv[..., 1] <= ch - 1)
    ui = np.rint(np.clip(np.nan_to_num(uv[..., 0]), 0, cw - 1)).astype(int)
    vi = np.rint(np.clip(np.nan_to_num(uv[..., 1]), 0, ch - 1)).astype(int)
    sup_r = orec["raw_support_R"][vi, ui]
    same = orec["right_reprojection_instance"] == ids_l
    nonly = N & ~R
    left = nonly.copy()
    reasons = {}
    for name, m in (("no_geometry", ~geom), ("O_0_noncatalog_geometry", (ids_l == 0) & geom),
                    ("right_reprojection_outside_core", ~inside), ("right_pixel_unsupported", ~sup_r),
                    ("different_right_instance", ~same)):
        reasons[name] = int((left & m).sum())
        left &= ~m
    reasons["other"] = int(left.sum())
    per_instance = []
    for i in sorted(set(ids_l[overlap].tolist())):
        m = overlap & (ids_l == i)
        if int(m.sum()) >= SP.MIN_INSTANCE_OVERLAP:
            per_instance.append({"instance_id": int(i), "object_name": names.get(int(i), ""), **_errors(xyz_n, xyz_r, m, c_l)})
    e3_map = np.where(overlap, np.linalg.norm(xyz_n - xyz_r, axis=-1), np.nan).astype(np.float32)
    rad_map = np.where(overlap, np.linalg.norm(xyz_n - c_l, axis=-1) - np.linalg.norm(xyz_r - c_l, axis=-1),
                       np.nan).astype(np.float32)
    first_hit = N & geom
    summary = {
        "schema": "AB1a-evaluation-summary-v1", "truth": SP.TRUTH_REFERENCE, "computed_after_freeze": True,
        "statement": "POST-FREEZE REFERENCE / EVALUATION: descriptive comparison of the frozen natural measurement with "
                     "the accepted Classroom-Oracle-1 local oracle at the same calibration and gaze; no pass / fail; "
                     "changes nothing in the measurement",
        "reference": {"implementation": "tools/classroom_oracle1_matcher.compute (accepted, read-only)", **ometa},
        "counts": {"core_pixels": int(N.size), "natural_valid": int(N.sum()), "reference_valid": int(R.sum()),
                   "overlap": int(overlap.sum()), "natural_only": int(nonly.sum()), "reference_only": int((R & ~N).sum())},
        "overlap_errors": _errors(xyz_n, xyz_r, overlap, c_l),
        "natural_vs_left_first_hit": {"definition": "every natural-valid pixel with left geometry (any index) against the "
                                                    "left first-hit Position at the same rectified pixel; no binocular-"
                                                    "visibility rule", **_errors(xyz_n, left_h, first_hit, c_l)},
        "composition_of_natural_valid": composition, "natural_only_reasons": reasons,
        "per_instance_errors": {"minimum_overlap_pixels": SP.MIN_INSTANCE_OVERLAP, "instances": per_instance},
        "reference_composition": {
            "reference_valid_instances": [{"instance_id": int(i), "object_name": names.get(int(i), ""), "pixels": int(k)}
                                          for i, k in zip(*np.unique(ids_l[R], return_counts=True))],
            "core_left_geometry_pixels": int(geom.sum()), "core_left_catalog_pixels": int((ids_l > 0).sum()),
            "core_left_O_0_pixels": int(((ids_l == 0) & geom).sum())},
        "camera_model": camera_model(c, {"L": ref["position_w_L"], "R": ref["position_w_R"]}),
        "error_fraction_scales_m": list(SP.ERROR_FRACTIONS_M), "quantiles": SP.QUANTILES,
    }
    arrays = {k: np.asarray(orec[k]) for k in ("xyz_h", "valid", "range_left_m", "instance_id", "raw_support_L",
                                                "raw_support_R", "instance_id_R", "right_reprojection_uv",
                                                "right_reprojection_instance", "crop_xywh")}
    arrays.update({"left_position_h": left_h.astype(np.float32), "left_geometry": geom, "overlap": overlap,
                   "error_3d_m": e3_map, "radial_signed_m": rad_map})
    return summary, arrays


def load_reference(path: Path) -> dict:
    with np.load(path, allow_pickle=False) as z:
        if set(z.files) != set(SP.REFERENCE_KEYS):
            raise SystemExit(f"{PREFIX} STOP reference observation arrays {sorted(z.files)}")
        return {k: np.asarray(z[k]) for k in SP.REFERENCE_KEYS}


def evaluate(run: Path) -> dict:
    out, ev = run / "evaluation", run / "evaluation_only"
    if (out / "evaluation-summary.json").exists():
        raise SystemExit(f"{PREFIX} STOP the evaluation exists")
    out.mkdir(parents=True, exist_ok=True)
    frozen = [run / n for n in SP.FROZEN_MEASUREMENT] + [run / "measurement/measurement-freeze.json"]
    refs = [ev / "reference-observation.npz", ev / "instance-catalog.json", SP.ACCEPTED_CATALOG[0]]
    with OpenGuard("evaluation", frozen + refs, [out]) as g:
        fz = verify_measurement_freeze(run)
        g.mark("measurement_freeze_verified")
        c = read_json(run / "acquisition/calibration.json")
        with np.load(run / "measurement/stereo-result.npz") as z:
            nat = {k: np.asarray(z[k]) for k in ("valid", "xyz_h")}
        rgb = ST.load_observation(run / "acquisition/rgb-observation.npz")
        g.mark("reference_access_begins")
        ref = load_reference(ev / "reference-observation.npz")
        cat = read_json(ev / "instance-catalog.json")["instances"]
        accepted = read_json(SP.ACCEPTED_CATALOG[0])["instances"]
        names = {int(e["instance_id"]): e["object_name"] for e in cat}
        summ, arrays = evaluation_core(c, nat, rgb, ref, names)
        summ["catalog_equals_accepted"] = cat == accepted
        summ["frozen_measurement_sha256"] = fz["files"]
        np.savez_compressed(out / "oracle-reference.npz", **arrays)
        write_json(out / "evaluation-summary.json", summ)
    rec = g.record()
    rec["ordered_data_events"] = [e.get("label") or e.get("path") for e in rec["events"]
                                  if e.get("event") == "mark" or e.get("kind") == "data-read"]
    rec["truth_firewall_violations"] = len(rec["violations"])
    write_json(out / "evaluation-opened-files.json", rec)
    verify_measurement_freeze(run)
    if rec["violations"]:
        raise SystemExit(f"{PREFIX} STOP evaluation guard violations: {rec['violations']}")
    k, e = summ["counts"], summ["overlap_errors"]["error_3d_m"]
    print(f"{PREFIX} evaluate: natural {k['natural_valid']}, reference {k['reference_valid']}, overlap {k['overlap']}, "
          f"natural-only {k['natural_only']}, reference-only {k['reference_only']}; 3-D error "
          f"{'none' if e is None else round(e['median'], 5)}; camera model ok {summ['camera_model']['ok']}; "
          f"frozen measurement re-verified")
    return summ


# ------------------------------------------------------------------ synthetic known answers (section 15)
def noise_texture(seed: int, n: int = 1400, sigma: float = 1.2) -> np.ndarray:
    import cv2
    rng = np.random.default_rng(seed)
    t = cv2.GaussianBlur(rng.random((n, n, 3)).astype(np.float32), (0, 0), sigma)
    return 0.05 + 0.9 * (t - t.min()) / (t.max() - t.min())


def rect_axis_h(c: dict, r: dict) -> np.ndarray:
    c_l = np.asarray(c["eyes"][0]["centre_h_m"], float)
    return FG.unit(FG.rect_to_head(c, r["R1"], np.array([0.0, 0.0, 1.0])) - c_l)


def render_planes(c: dict, planes: list[dict]) -> tuple[dict, dict]:
    """Analytic L / R tangent images of textured planes (nearest hit), plus synthetic truth (plane id, Position).
    Each plane: normal ``n`` (head frame), rectified depth ``z`` from the left eye centre along ``n``, optional
    half-extent ``half`` (m) around its foot point, texture ``tex`` sampled at ``spacing`` m per texel."""
    import cv2
    w, h = c["image_size_wh"]
    uv = FG.pixels(w, h)
    c_l = np.asarray(c["eyes"][0]["centre_h_m"], float)
    rgb, truth = {}, {}
    for i, side in enumerate(("L", "R")):
        eye = c["eyes"][i]
        o = np.asarray(eye["centre_h_m"], float)
        d = FG.rays_h(eye, uv)
        best_t = np.full((h, w), np.inf)
        img = np.zeros((h, w, 3), np.float32)
        pid = np.zeros((h, w), np.int32)
        for k, p in enumerate(planes, start=1):
            n = FG.unit(np.asarray(p["n"], float))
            foot = c_l + n * p["z"]
            a = FG.unit(np.cross(n, [0.0, 1.0, 0.0]) if abs(n[1]) < 0.9 else np.cross(n, [1.0, 0.0, 0.0]))
            b = np.cross(n, a)
            with np.errstate(divide="ignore", invalid="ignore"):
                t = (p["z"] - (o - c_l) @ n) / (d @ n)
            X = o + d * t[..., None]
            qa, qb = (X - foot) @ a, (X - foot) @ b
            ok = np.isfinite(t) & (t > 0) & (t < best_t)
            if p.get("half") is not None:
                ok &= (np.abs(qa) <= p["half"][0]) & (np.abs(qb) <= p["half"][1])
            tex = p["tex"]
            sx = (qa / p.get("spacing", 0.004) + tex.shape[1] / 2).astype(np.float32)
            sy = (qb / p.get("spacing", 0.004) + tex.shape[0] / 2).astype(np.float32)
            col = cv2.remap(tex, sx, sy, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
            img[ok] = col[ok]
            pid[ok] = k
            best_t = np.where(ok, t, best_t)
        pos_h = o + d * np.where(np.isfinite(best_t), best_t, 0.0)[..., None]
        rgb[f"rgb_{side}"] = np.clip(img, 0, 1).astype(np.float32)
        truth[f"instance_{side}"] = pid
        truth[f"position_w_{side}"] = np.where((pid > 0)[..., None], FG.head_to_world(c, pos_h), 0.0).astype(np.float32)
    return rgb, truth


def _plane_case(c: dict, z: float, seed: int = 1, half=None) -> tuple[dict, dict, dict]:
    r = FS.rectification(c)
    rgb, truth = render_planes(c, [{"n": rect_axis_h(c, r), "z": z, "tex": noise_texture(seed), "half": half}])
    return r, rgb, truth


def synthetic_cases() -> list[tuple]:
    fwd = FG.make_calibration(SP.PROFILE, 0.0, 0.0, SP.VERGENCE_M, tangent_frame=SP.TANGENT_FRAME)
    cases = []

    def plane(v):
        r, rgb, _ = _plane_case(fwd, SP.SYN_PLANE_Z_M)
        rec, s = ST.compute_natural(fwd, rgb, v)
        m = rec["valid"]
        d_true = -float(r["P2"][0, 3]) / SP.SYN_PLANE_Z_M
        e = rec["disparity_px"][m] - d_true
        n = rect_axis_h(fwd, r)
        c_l = np.asarray(fwd["eyes"][0]["centre_h_m"])
        plane_res = np.abs((rec["xyz_h"][m].astype(np.float64) - c_l) @ n - SP.SYN_PLANE_Z_M)
        det = {"valid_fraction": float(m.mean()), "d_true": d_true,
               "median_d_error": float(np.median(e)) if e.size else None,
               "p95_abs_d_error": float(np.quantile(np.abs(e), 0.95)) if e.size else None,
               "median_z_rel": float(np.median(np.abs(rec["z_rect_m"][m] - SP.SYN_PLANE_Z_M)) / SP.SYN_PLANE_Z_M) if e.size else None,
               "median_plane_m": float(np.median(plane_res)) if e.size else None}
        ok = (e.size and det["valid_fraction"] >= SP.SYN_MIN_VALID and abs(det["median_d_error"]) <= SP.SYN_MAX_MEDIAN_DISPARITY_PX
              and det["p95_abs_d_error"] <= SP.SYN_MAX_P95_DISPARITY_PX and det["median_z_rel"] <= SP.SYN_MAX_MEDIAN_Z_REL
              and det["median_plane_m"] <= SP.SYN_MAX_MEDIAN_PLANE_M)
        return bool(ok), det
    cases.append(("textured fronto-parallel plane at z_rect 2 m: disparity and geometry recovered", plane))

    def uniform(v):
        rgb = {k: np.full((SP.RAW_SIZE, SP.RAW_SIZE, 3), 0.3, np.float32) for k in SP.RGB_KEYS}
        rec, _ = ST.compute_natural(fwd, rgb, v)
        return int(rec["valid"].sum()) == 0 and not rec["term_texture"].any(), {
            "valid": int(rec["valid"].sum()), "texture_pass": int(rec["term_texture"].sum())}
    cases.append(("low-texture (uniform) pair: the texture gate rejects it", uniform))

    def lr_case(v):
        r, rgb, _ = _plane_case(fwd, SP.SYN_PLANE_Z_M)
        bad = dict(rgb)
        right = rgb["rgb_R"].copy()
        right[260:380, 280:400] = noise_texture(99)[:120, :120]
        bad["rgb_R"] = right
        rec, _ = ST.compute_natural(fwd, bad, v)
        off, _ = ST.compute_natural(fwd, bad, {**v, "use_lr": False})
        x, y, cw, ch = map(int, r["crop_xywh"])
        d_true = -float(r["P2"][0, 3]) / SP.SYN_PLANE_Z_M
        vv, uu = np.mgrid[y:y + ch, x:x + cw].astype(np.float32)
        sx = r["map_Rx"][vv.astype(int), np.clip(np.rint(uu - d_true).astype(int), 0, SP.RAW_SIZE - 1)]
        sy = r["map_Ry"][vv.astype(int), np.clip(np.rint(uu - d_true).astype(int), 0, SP.RAW_SIZE - 1)]
        aff = (sx >= 280 + 4) & (sx < 400 - 4) & (sy >= 260 + 4) & (sy < 380 - 4)
        with_lr, without = int((rec["valid"] & aff).sum()), int((off["valid"] & aff).sum())
        inconsistent = int((~rec["term_lr"] & aff & rec["term_sgbm_left"]).sum())
        ok = (aff.sum() > 1000 and not (rec["valid"] & (rec["lr_error_px"] > 1.0)).any()
              and with_lr <= 0.2 * aff.sum() and without >= with_lr + 100)
        return bool(ok), {"affected": int(aff.sum()), "valid_affected_with_lr": with_lr,
                          "valid_affected_without_lr": without, "sgbm_valid_lr_rejected_affected": inconsistent}
    cases.append(("explicit left/right inconsistency: LR consistency rejects the affected pixels", lr_case))

    def occlusion(v):
        r = FS.rectification(fwd)
        n = rect_axis_h(fwd, r)
        planes = [{"n": n, "z": 3.0, "tex": noise_texture(3)},
                  {"n": n, "z": 1.5, "tex": noise_texture(4), "half": (0.06, 0.5)}]
        rgb, truth = render_planes(fwd, planes)
        rec, _ = ST.compute_natural(fwd, rgb, v)
        x, y, cw, ch = map(int, r["crop_xywh"])
        import cv2
        pid = FS.remap(truth["instance_L"].astype(np.float32), r, "L", cv2.INTER_NEAREST)[y:y + ch, x:x + cw].astype(int)
        pos = FS.remap(truth["position_w_L"], r, "L", cv2.INTER_NEAREST)[y:y + ch, x:x + cw].astype(np.float64)
        ph = FG.world_to_head(fwd, pos)
        # half-occlusion: far-plane points whose segment to the right eye crosses the near plane's extent
        o_r = np.asarray(fwd["eyes"][1]["centre_h_m"], float)
        c_l = np.asarray(fwd["eyes"][0]["centre_h_m"], float)
        dd = ph - o_r
        with np.errstate(divide="ignore", invalid="ignore"):
            t = (1.5 - (o_r - c_l) @ n) / (dd @ n)
        hit = o_r + dd * t[..., None] - (c_l + n * 1.5)
        a = FG.unit(np.cross(n, [0.0, 1.0, 0.0]))
        b = np.cross(n, a)
        blocked = (pid == 1) & (t > 0) & (t < 1) & (np.abs(hit @ a) <= 0.06) & (np.abs(hit @ b) <= 0.5)
        m = rec["valid"]
        zz = rec["z_rect_m"]
        near_med = float(np.nanmedian(zz[m & (pid == 2)])) if (m & (pid == 2)).any() else None
        far_med = float(np.nanmedian(zz[m & (pid == 1) & ~blocked])) if (m & (pid == 1) & ~blocked).any() else None
        keys_ok = not any(k for k in rec if any(s in k.lower() for s in ("instance", "position", "object", "truth")))
        ok = (keys_ok and near_med is not None and far_med is not None and abs(near_med - 1.5) <= 0.015
              and abs(far_med - 3.0) <= 0.03 and blocked.sum() > 100)
        wrong = int((m & blocked & (np.abs(zz - 3.0) > 0.05)).sum())
        return bool(ok), {"result_has_no_identity_field": keys_ok, "near_median_z": near_med, "far_median_z": far_med,
                          "half_occluded_pixels": int(blocked.sum()), "half_occluded_valid": int((m & blocked).sum()),
                          "half_occluded_valid_off_by_more_than_5cm": wrong,
                          "note": "descriptive: no identity mask exists; the half-occluded strip's validity is recorded"}
    cases.append(("occlusion: no identity mask; both depths recovered; half-occluded strip recorded", occlusion))

    def outside(v):
        """Far plane (8 m, inside the search but beyond z_rect 4.5 m): rejected entirely.  Near plane (0.5 m, true
        disparity beyond the search): the true geometry is never admitted; in-range false matches that survive the
        gates are counted (implementation-time clarification of contract section 15, case 5)."""
        det, ok = {}, True
        for z in (0.5, 8.0):
            r, rgb, _ = _plane_case(fwd, z)
            rec, _ = ST.compute_natural(fwd, rgb, v)
            m = rec["valid"]
            zz = rec["z_rect_m"][m]
            d_true = -float(r["P2"][0, 3]) / z
            det[f"z_{z}"] = {"valid": int(m.sum()), "true_disparity_px": d_true,
                             "num_disparities": int(r["num_disparities"]),
                             "valid_within_20pct_of_true_z": int((np.abs(zz - z) <= 0.2 * z).sum()),
                             "valid_z_rect_m": _q(zz, SP.SUMMARY_QUANTILES)}
            if z < SP.Z_RECT_M[0]:
                ok &= d_true > int(r["num_disparities"]) and det[f"z_{z}"]["valid_within_20pct_of_true_z"] == 0
            else:
                ok &= int(m.sum()) == 0
        return bool(ok), det
    cases.append(("outside the fixed search / z_rect interval: 8 m rejected; 0.5 m true geometry never admitted",
                  outside))

    def support(v):
        c = FG.make_calibration(SP.PROFILE, 0.0, 0.0, SP.SYN_SUPPORT_VERGENCE_M, tangent_frame=SP.TANGENT_FRAME)
        r, rgb, _ = _plane_case(c, 1.0)
        rec, _ = ST.compute_natural(c, rgb, v)
        sup = rec["raw_support_L"]
        outside_valid = int((rec["valid"] & ~sup).sum())
        ok = (~sup).sum() > 0 and outside_valid == 0 and rec["valid"].sum() > 0.5 * sup.sum()
        return bool(ok), {"supported": int(sup.sum()), "unsupported": int((~sup).sum()), "valid": int(rec["valid"].sum()),
                          "valid_outside_support": outside_valid}
    cases.append(("calibration support border (vergence 0.15 m): no valid pixel outside the support", support))

    def gaze1(v):
        c = FG.make_calibration(SP.PROFILE, SP.GAZE_YAW_DEG, SP.GAZE_PITCH_DEG, SP.VERGENCE_M,
                                tangent_frame=SP.TANGENT_FRAME)
        r = FS.rectification(c)
        geo = ST.prelook_geometry(c)
        d = FG.gaze_direction(SP.GAZE_YAW_DEG, SP.GAZE_PITCH_DEG)
        n = FG.unit(d)
        rgb, _ = render_planes(c, [{"n": n, "z": 2.1, "tex": noise_texture(5)}])
        rec, s = ST.compute_natural(c, rgb, v)
        mats = all(np.isfinite(np.asarray(r[k], float)).all() for k in ("R1", "R2", "P1", "P2", "Q_full"))
        lev = math.sqrt(1 - (math.sin(math.radians(SP.GAZE_YAW_DEG)) * math.cos(math.radians(SP.GAZE_PITCH_DEG))) ** 2)
        fin = bool(np.isfinite(rec["xyz_h"][rec["valid"]]).all())
        ok = mats and fin and abs(geo["L"] - lev) <= 1e-12 and math.isfinite(geo["B_perp_m"])
        return bool(ok), {"L": geo["L"], "B_perp_m": geo["B_perp_m"], "rectification_finite": mats,
                          "synthetic_plane_valid": s["valid_count"],
                          "core_centre_from_gaze_deg": geo["eyes"]["L"]["rectified_core_centre_from_gaze_deg"]}
    cases.append(("baseline-projected gaze #1: calibration and rectification accepted and finite", gaze1))

    def degenerate(v):
        got = {}
        for yaw in (-90.0, 90.0):
            try:
                FG.make_calibration(SP.PROFILE, yaw, 0.0, SP.VERGENCE_M, tangent_frame=SP.TANGENT_FRAME)
                got[str(yaw)] = "accepted"
            except ValueError as exc:
                got[str(yaw)] = str(exc)
        return all("stereo baseline" in s for s in got.values()), got
    cases.append(("exact gaze along +/- baseline: rejected as the tangent-frame degeneracy", degenerate))

    def truth_independence(kind):
        def fn(v):
            import tempfile
            r, rgb, truth = _plane_case(fwd, SP.SYN_PLANE_Z_M, half=(0.3, 0.3))
            with tempfile.TemporaryDirectory(prefix="ab1a-syn-") as td:
                td = Path(td)
                acq, ev = td / "acquisition", td / "evaluation_only"
                acq.mkdir()
                ev.mkdir()
                write_json(acq / "calibration.json", fwd)
                np.savez_compressed(acq / "rgb-observation.npz", **rgb)
                np.savez_compressed(ev / "reference-observation.npz", **truth)
                s1, g1 = ST.measure_dir(acq, td / "m1", v)
                alt = dict(truth)
                if kind == "id":
                    alt["instance_L"] = (truth["instance_L"] * 7 + 3).astype(np.int32)
                    alt["instance_R"] = np.zeros_like(truth["instance_R"])
                else:
                    alt["position_w_L"] = (truth["position_w_L"] * 1.5 + 0.2).astype(np.float32)
                    alt["position_w_R"] = np.zeros_like(truth["position_w_R"])
                (ev / "reference-observation.npz").unlink()
                np.savez_compressed(ev / "reference-observation.npz", **alt)
                s2, g2 = ST.measure_dir(acq, td / "m2", v)
                with np.load(td / "m1/stereo-result.npz") as a, np.load(td / "m2/stereo-result.npz") as b:
                    same = sorted(a.files) == sorted(b.files) and all(a[k].tobytes() == b[k].tobytes() for k in a.files)
                strip = lambda s: {k: x for k, x in s.items() if k != "seconds"}  # noqa: E731
                reads = [sorted(Path(p).name for p in g["data_reads"]) for g in (g1, g2)]
            ok = same and strip(s1) == strip(s2) and reads == [["calibration.json", "rgb-observation.npz"]] * 2
            return bool(ok), {"arrays_identical": same, "summary_identical_except_runtime": strip(s1) == strip(s2),
                              "data_reads": reads, "valid": s1["valid_count"]}
        return fn
    cases.append(("synthetic Object Index truth changed, RGB byte-identical: measurement array-identical",
                  truth_independence("id")))
    cases.append(("synthetic Position truth changed, RGB byte-identical: measurement array-identical",
                  truth_independence("position")))

    def guard(v):
        import tempfile
        r, rgb, truth = _plane_case(fwd, SP.SYN_PLANE_Z_M)
        with tempfile.TemporaryDirectory(prefix="ab1a-syn-") as td:
            td = Path(td)
            acq, ev = td / "acquisition", td / "evaluation_only"
            acq.mkdir()
            ev.mkdir()
            write_json(acq / "calibration.json", fwd)
            np.savez_compressed(acq / "rgb-observation.npz", **rgb)
            np.savez_compressed(ev / "reference-observation.npz", **truth)
            try:
                ST.measure_dir(acq, td / "m", v, probe=ev / "reference-observation.npz")
                raised = None
            except PermissionError as exc:
                raised = str(exc)
            rec = read_json(td / "m/measurement-opened-files.json")
        ok = raised is not None and len(rec["violations"]) == 1 and "evaluation_only" in rec["violations"][0]["path"]
        return bool(ok), {"raised": raised, "violations": len(rec["violations"])}
    cases.append(("opening an evaluation-only file during measurement: the truth guard fails", guard))

    def refuse(v):
        _r, rgb, truth = _plane_case(fwd, SP.SYN_PLANE_Z_M)
        try:
            ST.compute_natural(fwd, {**rgb, "instance_L": truth["instance_L"]}, v)
        except ValueError as exc:
            return True, {"refused": str(exc)}
        return False, {"refused": False}
    cases.append(("an observation carrying anything besides rgb_L / rgb_R is refused", refuse))
    return cases


def _jsonable(x):
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    if isinstance(x, np.ndarray):
        return _jsonable(x.tolist())
    if isinstance(x, (np.bool_,)):
        return bool(x)
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, np.floating):
        return float(x)
    return x


def synthetic_results(**variant) -> list[dict]:
    out = []
    for name, fn in synthetic_cases():
        try:
            ok, detail = fn(variant)
        except Exception as exc:  # a crash is a failed known answer, recorded
            ok, detail = False, {"raised": f"{type(exc).__name__}: {exc}"}
        out.append({"name": name, "ok": bool(ok), "detail": _jsonable(detail)})
    return out


def synthetic(run: Path) -> dict:
    out = run / "synthetic"
    out.mkdir(parents=True, exist_ok=True)
    results = synthetic_results()
    for x in results:
        print(f"{PREFIX} synthetic {'PASS' if x['ok'] else 'FAIL'} {x['name']}")
    rep = {"schema": "AB1a-synthetic-report-v1", "code": code_state(), "cases": results,
           "passed": all(x["ok"] for x in results),
           "thresholds": {k: getattr(SP, k) for k in dir(SP) if k.startswith("SYN_")},
           "note": "analytic textured-plane pairs through the accepted calibration; no Blender, no Classroom"}
    write_json(out / "synthetic-report.json", rep)
    print(f"{PREFIX} synthetic {sum(x['ok'] for x in results)}/{len(results)} "
          f"{'AB1A_SYNTHETIC_PASS' if rep['passed'] else 'FAILED'}")
    return rep


# ------------------------------------------------------------------ Blender rehearsal (synthetic scene only)
def exr_passes(channels: list[str]) -> set:
    return {".".join(ch.split(".")[1:-1]) for ch in channels}


def rehearse(run: Path) -> dict:
    root = run / "synthetic/blender-rehearsal"
    if root.exists():
        shutil.rmtree(root)
    res = blender(run, "rehearsal", None, run / "logs/rehearsal-blender.log")
    if not res["blender"]["complete_marker"]:
        raise SystemExit(f"{PREFIX} rehearsal Blender run failed; see {res['blender']['log']}")
    report = {"schema": "AB1a-blender-rehearsal-v1", "code": code_state(), "scene": "synthetic factory-startup room",
              "classroom_used": False, "cases": {}}
    ok_all = True
    for case in SP.REHEARSAL_GAZES:
        d = root / case
        a = read_json(d / "acquisition/acquisition.json")
        c = read_json(d / "acquisition/calibration.json")
        summ, rec = ST.measure_dir(d / "acquisition", d / "measurement")
        nat_arrays = np.load(d / "measurement/stereo-result.npz")
        nat = {k: np.asarray(nat_arrays[k]) for k in ("valid", "xyz_h")}
        rgb = ST.load_observation(d / "acquisition/rgb-observation.npz")
        ref = load_reference(d / "evaluation_only/reference-observation.npz")
        ev, _arrays = evaluation_core(c, nat, rgb, ref, {})
        passes = {s: sorted(exr_passes(a["exr_channels_lr"][s])) for s in ("L", "R")}
        st = a["settings"]
        checks = {"camera_model": ev["camera_model"]["ok"],
                  "exr_passes": all(set(p) == set(SP.PASSES) for p in passes.values()),
                  "settings": (st["samples"] == SP.REHEARSAL_SPP and st["pixel_filter"] == "BOX"
                               and not st["adaptive_sampling"] and not st["denoising"] and a["device"] == SP.DEVICE
                               and a["render_seeds_lr"] == SP.SEEDS),
                  "guard": rec["violations"] == [] and len(rec["data_reads"]) == 2}
        rad = ev["overlap_errors"]["radial_abs_m"]
        if case == "forward":
            checks["forward_valid_fraction"] = summ["valid_fraction_core"] >= SP.REHEARSAL_MIN_VALID
            checks["forward_median_radial"] = rad is not None and rad["median"] <= SP.REHEARSAL_MAX_MEDIAN_RADIAL_M
        ok_all &= all(checks.values())
        report["cases"][case] = {"gaze": a["gaze_yaw_pitch_deg"], "checks": checks, "exr_passes": passes,
                                 "render_seconds": a["render_seconds_lr"], "natural_valid": summ["valid_count"],
                                 "natural_valid_fraction": summ["valid_fraction_core"],
                                 "counts": ev["counts"], "overlap_radial_abs_m": rad,
                                 "overlap_error_3d_m": ev["overlap_errors"]["error_3d_m"],
                                 "camera_model": ev["camera_model"]}
        print(f"{PREFIX} rehearsal {case}: {checks}; natural valid {summ['valid_fraction_core']:.4f}; radial "
              f"{None if rad is None else round(rad['median'], 5)}")
    report["passed"] = bool(ok_all)
    write_json(root / "rehearsal-report.json", _jsonable(report))
    print(f"{PREFIX} rehearsal {'AB1A_REHEARSAL_PASS' if ok_all else 'FAILED'}")
    return report


# ------------------------------------------------------------------ manifest
def write_manifest(run: Path) -> dict:
    files = sorted(str(p.relative_to(run)) for p in run.rglob("*") if p.is_file()
                   and p.name not in ("manifest.json", "check-summary.json", "process-log.jsonl"))
    m = {"schema": "AB1a-manifest-v1", "experiment": SP.EXPERIMENT, "contract": SP.CONTRACT, "code": code_state(),
         "base_commit": SP.BASE_COMMIT, "action_source": SP.ACTION_SOURCE,
         "nb1c": {"freeze": SP.NB1C_FREEZE[1], "candidate_gazes": SP.NB1C_CANDIDATES[1], "manifest": SP.NB1C_MANIFEST[1]},
         "truth": {"source/": SP.TRUTH_DERIVED, "prelook/": SP.TRUTH_DERIVED, "acquisition/": SP.TRUTH_ORACLE,
                   "evaluation_only/": SP.TRUTH_REFERENCE, "measurement/": SP.TRUTH_DERIVED,
                   "evaluation/": SP.TRUTH_REFERENCE, "synthetic/": "known answers"},
         "files": {f: sha256(run / f) for f in files}}
    write_json(run / "manifest.json", m)
    return m


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("synthetic", "rehearse", "prelook", "preflight", "acquire", "measure", "freeze", "evaluate",
                 "visualize"):
        p = sub.add_parser(name)
        p.add_argument("--run", required=True, type=Path)
        if name == "visualize":
            p.add_argument("--visuals", required=True, type=Path)
    a = ap.parse_args(argv)
    run = a.run.resolve()
    t0 = time.time()
    status, extra = "failed", {}
    try:
        if a.cmd == "synthetic":
            ok = synthetic(run)["passed"]
            status = "ok" if ok else "failed"
            return 0 if ok else 1
        if a.cmd == "rehearse":
            ok = rehearse(run)["passed"]
            status = "ok" if ok else "failed"
            return 0 if ok else 1
        if a.cmd == "prelook":
            prelook(run)
        elif a.cmd == "preflight":
            extra = preflight(run)
        elif a.cmd == "acquire":
            extra = acquire(run)
            if not extra["blender"]["complete_marker"]:
                return 1
        elif a.cmd == "measure":
            measure(run)
        elif a.cmd == "freeze":
            freeze(run)
        elif a.cmd == "evaluate":
            evaluate(run)
        elif a.cmd == "visualize":
            import ab1a_visuals
            ab1a_visuals.visualize(run, a.visuals.resolve())
            write_manifest(run)
        status = "ok"
        return 0
    finally:
        log_process(run, a.cmd, t0, status, extra)


if __name__ == "__main__":
    raise SystemExit(main())
