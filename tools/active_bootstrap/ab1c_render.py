"""Active Bootstrap-1c: the Blender side (preflight, the three canonical binocular observations, rehearsal).

Contract: docs/active-bootstrap/ab1c-safe-forward-planar-vs-spherical-contract.md, sections 6 and 14.  Normally run
through ``ab1c_run.py``:

    blender -b scenes/classroom/classroom_eye.blend --python-exit-code 1 \
        -P tools/active_bootstrap/ab1c_render.py -- --mode preflight --run RUN --head-pose SEEDS
    blender -b scenes/classroom/classroom_eye.blend --python-exit-code 1 \
        -P tools/active_bootstrap/ab1c_render.py -- --mode canonical --run RUN --head-pose SEEDS
    blender -b --factory-startup --python-exit-code 1 \
        -P tools/active_bootstrap/ab1c_render.py -- --mode rehearsal --run RUN --head-pose SEEDS

A thin driver: the accepted AB1a acquisition helpers are imported read-only from ``ab1a_render`` (``eye_pose``,
``calibration``, ``configure``, ``acquire_pair``, ``calib_diff``, ``build_rehearsal_scene``) with
``classroom_oracle1_render._assign_instance_ids``; no accepted renderer is modified.  ``preflight`` stops before any
render.  ``canonical`` renders exactly one L/R pair at each of the three frozen SAFE-FORWARD gazes, in rank order, into
new directories, and splits each at once into the inference-visible RGB observation and the evaluation-only truth.
``rehearsal`` uses the accepted synthetic factory-startup room (never Classroom).  Every failure exits nonzero.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import traceback

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

import ab1a_render as AR  # noqa: E402  (accepted AB1a Blender acquisition helpers, read-only)
import ab1c_spec as SP  # noqa: E402

PREFIX = "[ab1c-render]"


def planned(run: Path) -> list[tuple[str, dict]]:
    out = []
    for g in SP.GAZES:
        out.append((g, json.loads((run / "plan" / g / "planned-calibration.json").read_text())))
    return out


def built_calibration(plan: dict, pose: dict) -> tuple[dict, float]:
    yaw, pitch = plan["gaze_yaw_pitch_deg"]
    c = AR.calibration(yaw, pitch, pose)
    diff = AR.calib_diff(plan, json.loads(json.dumps(c)))
    if not diff <= SP.CALIBRATION_TOL:
        raise RuntimeError(f"the calibration built from the EYE differs from the planned calibration ({diff})")
    return c, diff


def preflight(a) -> None:
    import bpy
    import classroom_oracle1_render as CO
    run = Path(a.run).resolve()
    out = AR.new_dir(run / "preflight")
    pose = AR.eye_pose(Path(a.head_pose))
    gazes = {}
    for g, plan in planned(run):
        c, diff = built_calibration(plan, pose)
        scene, cam, backend, matrix = AR.configure(c, SP.SPP)
        mats = {}
        for eye in c["eyes"]:
            cam.matrix_world = CO._eye_matrix(c, eye, matrix)
            bpy.context.view_layer.update()
            mats[eye["name"]] = [[cam.matrix_world[i][j] for j in range(4)] for i in range(4)]
        gazes[g] = {"gaze_yaw_pitch_deg": c["gaze_yaw_pitch_deg"], "calibration_max_abs_diff_from_planned": diff,
                    "device": backend, "settings": AR.readback(scene, cam), "camera_matrix_world_lr": mats}
    AR.write_json(out / "preflight.json", {
        "schema": "AB1c-preflight-v1", "statement": "Classroom loaded and configured for the three frozen gazes; NO render",
        "blend": bpy.data.filepath, "blender": bpy.app.version_string, "eye_pose": pose, "gazes": gazes,
        "rendered": False})
    print(f"{PREFIX} COMPLETE preflight (no render)", flush=True)


def canonical(a) -> None:
    import classroom_oracle1_render as CO
    run = Path(a.run).resolve()
    obs = run / "observations"
    if obs.exists() and any(obs.iterdir()):
        raise FileExistsError(f"STOP {obs} exists: each frozen gaze is observed once")
    plans = planned(run)
    pose = AR.eye_pose(Path(a.head_pose))
    ev_all = AR.new_dir(obs / "evaluation_only")
    by_id, _by_name = CO._assign_instance_ids()   # writes the evaluation-only Object Index pass only
    AR.write_json(ev_all / "instance-catalog.json", {
        "schema": "AB1c-instance-catalog-v1", "truth": SP.TRUTH_REFERENCE,
        "instances": [{"instance_id": int(k), "object_name": v} for k, v in sorted(by_id.items())]})
    done = {}
    for rank, (g, plan) in enumerate(plans, start=1):
        c, diff = built_calibration(plan, pose)
        acq, ev = AR.new_dir(obs / g / "acquisition"), AR.new_dir(obs / g / "evaluation_only")
        rec = AR.acquire_pair(c, acq, ev, SP.SPP, {
            "experiment": SP.EXPERIMENT, "action_source": f"frozen AB1c SAFE-FORWARD gaze #{rank}", "ab1c_gaze": g,
            "ab1c_rank": rank, "eye_pose": pose, "canonical": True, "calibration_max_abs_diff_from_planned": diff})
        done[g] = {"gaze": rec["gaze_yaw_pitch_deg"], "device": rec["device"], "seconds": rec["render_seconds_lr"]}
        print(f"{PREFIX} observed {g} " + json.dumps(done[g], sort_keys=True), flush=True)
    print(f"{PREFIX} COMPLETE canonical " + json.dumps(done, sort_keys=True), flush=True)


def rehearsal(a) -> None:
    import classroom_oracle1_render as CO
    run = Path(a.run).resolve()
    root = AR.new_dir(run / "synthetic/blender-rehearsal")
    AR.build_rehearsal_scene(Path(a.head_pose))
    pose = AR.eye_pose(Path(a.head_pose))
    by_id, _ = CO._assign_instance_ids()
    AR.write_json(root / "instance-catalog.json", {"instances": [{"instance_id": int(k), "object_name": v}
                                                                 for k, v in sorted(by_id.items())]})
    done = {}
    for case, (yaw, pitch) in SP.SYN_GAZES.items():
        acq, ev = AR.new_dir(root / case / "acquisition"), AR.new_dir(root / case / "evaluation_only")
        c = AR.calibration(yaw, pitch, pose)
        rec = AR.acquire_pair(c, acq, ev, SP.REHEARSAL_SPP, {"rehearsal": True, "experiment": SP.EXPERIMENT,
                                                             "scene": "synthetic factory-startup room", "eye_pose": pose})
        done[case] = rec["render_seconds_lr"]
    print(f"{PREFIX} COMPLETE rehearsal " + json.dumps(done, sort_keys=True), flush=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mode", required=True, choices=("preflight", "canonical", "rehearsal"))
    ap.add_argument("--run", required=True)
    ap.add_argument("--head-pose", required=True)
    a = ap.parse_args(AR.args_after_dashes())
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
