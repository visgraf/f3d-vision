"""Active Bootstrap-1d2: the Blender side (no-render preflight, the canonical 4096-spp observations, rehearsal).

Contract: docs/active-bootstrap/ab1d2-4096spp-observation-quality-contract.md, sections 4-6 and 21.  Normally run
through ``ab1d2_run.py``:

    blender -b scenes/classroom/classroom_eye.blend --python-exit-code 1 \
        -P tools/active_bootstrap/ab1d2_render.py -- --mode preflight --run RUN --head-pose SEEDS
    blender -b scenes/classroom/classroom_eye.blend --python-exit-code 1 \
        -P tools/active_bootstrap/ab1d2_render.py -- --mode canonical --run RUN --head-pose SEEDS
    blender -b --factory-startup --python-exit-code 1 \
        -P tools/active_bootstrap/ab1d2_render.py -- --mode rehearsal --spp 256 --run RUN --head-pose SEEDS

A thin driver: the accepted AB1a acquisition helpers are imported read-only from ``ab1a_render`` (``eye_pose``,
``calibration``, ``configure``, ``readback``, ``acquire_pair``, ``calib_diff``, ``write_json``, ``new_dir``,
``build_rehearsal_scene``) with ``classroom_oracle1_render._assign_instance_ids`` / ``_eye_matrix``; no accepted
renderer is modified.  The ONE intentional change from the accepted AB1c canonical acquisition is ``spp = 4096``.  The
calibration used is the accepted AB1c ``calibration.json`` itself (its re-serialization must reproduce the file byte for
byte), after checking it against the calibration built from the EYE and the camera matrices against the AB1c record.
``canonical`` replicates the AB1c call sequence (instance ids, then one ``acquire_pair`` per gaze in rank order).
Every failure exits nonzero.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import traceback

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

import ab1a_render as AR  # noqa: E402  (accepted AB1a Blender acquisition helpers, read-only)
import ab1d2_spec as SP  # noqa: E402

PREFIX = "[ab1d2-render]"


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def accepted(g: str) -> tuple[dict, bytes, dict]:
    """The accepted AB1c calibration (dict and exact bytes) and acquisition record of gaze ``g``, hash-verified."""
    cal_b = SP.a1c_acq(g, "calibration.json").read_bytes()
    acq_b = SP.a1c_acq(g, "acquisition.json").read_bytes()
    if sha_bytes(cal_b) != SP.A1C_CALIBRATION[g] or sha_bytes(acq_b) != SP.A1C_ACQUISITION[g]:
        raise RuntimeError(f"STOP the accepted AB1c calibration / acquisition record of {g} changed")
    return json.loads(cal_b), cal_b, json.loads(acq_b)


def matrices(c: dict) -> dict:
    """The world matrices the accepted acquisition would set for both eyes (mathutils, as Blender stores them)."""
    from mathutils import Matrix
    import classroom_oracle1_render as CO
    out = {}
    for eye in c["eyes"]:
        m = CO._eye_matrix(c, eye, Matrix)
        out[eye["name"]] = [[float(m[i][j]) for j in range(4)] for i in range(4)]
    return out


def max_abs(a, b) -> float:
    return max(abs(float(x) - float(y)) for ra, rb in zip(a, b) for x, y in zip(ra, rb))


def prepare_gaze(g: str, pose: dict, strict: bool) -> tuple[dict, dict]:
    """Section 5: built-vs-accepted calibration, byte-exact re-serialization, camera matrices vs the AB1c record."""
    tab = SP.GAZE_TABLE[g]
    c_acc, cal_b, acq = accepted(g)
    built = AR.calibration(tab["yaw_deg"], tab["pitch_deg"], pose)
    diff = AR.calib_diff(c_acc, json.loads(json.dumps(built)))
    reser = (json.dumps(c_acc, indent=1, sort_keys=True, allow_nan=False) + "\n").encode()
    mats = matrices(c_acc)
    mat_diff = {s: max_abs(mats[s], acq["camera_matrix_world_lr"][s]) for s in ("L", "R")}
    rep = {"gaze": g, "calibration_max_abs_diff_built_vs_accepted": diff,
           "reserialized_calibration_byte_identical": reser == cal_b,
           "reserialized_calibration_sha256": sha_bytes(reser), "accepted_calibration_sha256": SP.A1C_CALIBRATION[g],
           "camera_matrix_max_abs_diff_vs_accepted": mat_diff, "camera_matrix_world_lr": mats,
           "gaze_yaw_pitch_deg": list(c_acc["gaze_yaw_pitch_deg"]),
           "gaze_matches_table": list(c_acc["gaze_yaw_pitch_deg"]) == [tab["yaw_deg"], tab["pitch_deg"]]}
    rep["ok"] = bool(diff <= SP.CALIBRATION_TOL and rep["reserialized_calibration_byte_identical"]
                     and max(mat_diff.values()) <= SP.EYE_POSE_TOL and rep["gaze_matches_table"])
    if strict and not rep["ok"]:
        raise RuntimeError(f"STOP BEFORE RENDERING: {g} calibration / camera identity failed: "
                           + json.dumps({k: v for k, v in rep.items() if k != 'camera_matrix_world_lr'}, sort_keys=True))
    return c_acc, rep


def settings_diff(new: dict, old: dict) -> dict:
    """Readback keys that differ, excluding the one intended change (samples)."""
    return {k: [old.get(k), new.get(k)] for k in sorted(set(new) | set(old)) if k != "samples" and new.get(k) != old.get(k)}


def preflight(a) -> None:
    import bpy
    run = Path(a.run).resolve()
    out = run / "preflight"
    if (out / "preflight.json").exists():
        raise FileExistsError(f"STOP {out / 'preflight.json'} exists: the Classroom preflight runs once")
    out.mkdir(parents=True, exist_ok=True)
    pose = AR.eye_pose(Path(a.head_pose))
    gazes = {}
    for g in SP.GAZES:
        c, rep = prepare_gaze(g, pose, strict=True)
        _, _, acq = accepted(g)
        scene, cam, backend, matrix = AR.configure(c, SP.SPP)
        import classroom_oracle1_render as CO
        set_mats = {}
        for eye in c["eyes"]:
            cam.matrix_world = CO._eye_matrix(c, eye, matrix)
            bpy.context.view_layer.update()
            set_mats[eye["name"]] = [[cam.matrix_world[i][j] for j in range(4)] for i in range(4)]
        rb = AR.readback(scene, cam)
        sd = settings_diff(rb, acq["settings"])
        set_diff = {s: max_abs(set_mats[s], acq["camera_matrix_world_lr"][s]) for s in ("L", "R")}
        ok = (rep["ok"] and not sd and rb["samples"] == SP.SPP and backend == SP.DEVICE
              and max(set_diff.values()) <= SP.EYE_POSE_TOL)
        if not ok:
            raise RuntimeError(f"STOP {g} preflight: settings differ {sd}; samples {rb['samples']}; device {backend}; "
                               f"set matrices {set_diff}")
        gazes[g] = {**{k: v for k, v in rep.items() if k != "camera_matrix_world_lr"}, "device": backend,
                    "settings": rb, "settings_differences_except_samples": sd, "camera_matrix_world_lr": set_mats,
                    "set_camera_matrix_max_abs_diff_vs_accepted": set_diff, "ok": ok}
    AR.write_json(out / "preflight.json", {
        "schema": "AB1d2-preflight-v1", "truth": SP.TRUTH_DERIVED,
        "statement": "Classroom loaded and configured at 4096 spp for the three accepted gazes; calibration, camera "
                     "matrices and settings checked against the accepted AB1c records; NO render",
        "blend": bpy.data.filepath, "blend_realpath": os.path.realpath(bpy.data.filepath),
        "blender": bpy.app.version_string, "eye_pose": pose, "spp": SP.SPP, "gazes": gazes, "rendered": False})
    print(f"{PREFIX} COMPLETE preflight (no render)", flush=True)


def canonical(a) -> None:
    import classroom_oracle1_render as CO
    run = Path(a.run).resolve()
    obs = run / "observations"
    if obs.exists() and any(obs.iterdir()):
        raise FileExistsError(f"STOP {obs} exists: each accepted gaze is re-observed once")
    pose = AR.eye_pose(Path(a.head_pose))
    prepared = [(g, *prepare_gaze(g, pose, strict=True)) for g in SP.GAZES]   # all three, before any scene change
    print(f"{PREFIX} calibration and camera identity verified for all gazes before rendering", flush=True)
    ev_all = AR.new_dir(obs / "evaluation_only")
    by_id, _by_name = CO._assign_instance_ids()   # as in AB1c: writes the evaluation-only Object Index pass only
    AR.write_json(ev_all / "instance-catalog.json", {
        "schema": "AB1d2-instance-catalog-v1", "truth": SP.TRUTH_REFERENCE,
        "instances": [{"instance_id": int(k), "object_name": v} for k, v in sorted(by_id.items())]})
    done = {}
    for rank, (g, c, rep) in enumerate(prepared, start=1):
        acq, ev = AR.new_dir(obs / g / "acquisition"), AR.new_dir(obs / g / "evaluation_only")
        rec = AR.acquire_pair(c, acq, ev, SP.SPP, {
            "experiment": SP.EXPERIMENT, "action_source": f"accepted AB1c SAFE-FORWARD gaze #{rank}, re-observed at "
                                                          f"{SP.SPP} spp", "ab1c_gaze": g, "ab1c_rank": rank,
            "eye_pose": pose, "canonical": True,
            "calibration_max_abs_diff_from_planned": rep["calibration_max_abs_diff_built_vs_accepted"],
            "observation_quality_control": {"accepted_spp": SP.ACCEPTED_SPP, "spp": SP.SPP,
                                            "accepted_acquisition_sha256": SP.A1C_ACQUISITION[g],
                                            "accepted_calibration_sha256": SP.A1C_CALIBRATION[g],
                                            "statement": "256 -> 4096 spp ONLY"}})
        if AR.sha256(acq / "calibration.json") != SP.A1C_CALIBRATION[g]:
            raise RuntimeError(f"{g} written calibration differs from the accepted AB1c calibration")
        done[g] = {"gaze": rec["gaze_yaw_pitch_deg"], "device": rec["device"], "spp": rec["spp"],
                   "seconds": rec["render_seconds_lr"]}
        print(f"{PREFIX} observed {g} " + json.dumps(done[g], sort_keys=True), flush=True)
    print(f"{PREFIX} COMPLETE canonical " + json.dumps(done, sort_keys=True), flush=True)


def rehearsal(a) -> None:
    """The accepted AB1a synthetic room (factory startup; never Classroom), one pair at the gaze-1 direction."""
    import classroom_oracle1_render as CO
    spp = int(a.spp)
    if spp not in SP.REHEARSAL_SPPS:
        raise ValueError(f"rehearsal spp must be one of {SP.REHEARSAL_SPPS}")
    run = Path(a.run).resolve()
    root = AR.new_dir(run / f"synthetic/rehearsal/spp-{spp}")
    AR.build_rehearsal_scene(Path(a.head_pose))
    pose = AR.eye_pose(Path(a.head_pose))
    g = SP.REHEARSAL_GAZE
    tab = SP.GAZE_TABLE[g]
    _c_acc, rep = prepare_gaze(g, pose, strict=False)          # recorded, not required, on the synthetic room
    c = AR.calibration(tab["yaw_deg"], tab["pitch_deg"], pose)
    by_id, _ = CO._assign_instance_ids()
    ev_all = AR.new_dir(root / "evaluation_only")
    AR.write_json(ev_all / "instance-catalog.json", {"instances": [{"instance_id": int(k), "object_name": v}
                                                                  for k, v in sorted(by_id.items())]})
    acq, ev = AR.new_dir(root / g / "acquisition"), AR.new_dir(root / g / "evaluation_only")
    rec = AR.acquire_pair(c, acq, ev, spp, {
        "experiment": SP.EXPERIMENT, "action_source": "rehearsal (synthetic factory-startup room)", "ab1c_gaze": g,
        "ab1c_rank": 1, "eye_pose": pose, "canonical": False,
        "calibration_max_abs_diff_from_planned": rep["calibration_max_abs_diff_built_vs_accepted"],
        "observation_quality_control": {"rehearsal": True, "spp": spp}})
    AR.write_json(root / "rehearsal-identity.json", {k: v for k, v in rep.items()})
    print(f"{PREFIX} COMPLETE rehearsal spp {spp} " + json.dumps(rec["render_seconds_lr"], sort_keys=True), flush=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mode", required=True, choices=("preflight", "canonical", "rehearsal"))
    ap.add_argument("--run", required=True)
    ap.add_argument("--head-pose", required=True)
    ap.add_argument("--spp", type=int, default=None)
    a = ap.parse_args(AR.args_after_dashes())
    if a.mode != "rehearsal" and a.spp is not None:
        raise ValueError("--spp is a rehearsal option only; the canonical spp is the declared constant")
    {"preflight": preflight, "canonical": canonical, "rehearsal": rehearsal}[a.mode](a)


if __name__ == "__main__":
    try:
        main()
    except BaseException as exc:
        if isinstance(exc, SystemExit) and exc.code in (0, None):
            raise
        traceback.print_exc()
        print(f"{PREFIX} FAILED", flush=True)
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)
