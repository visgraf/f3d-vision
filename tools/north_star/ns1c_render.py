"""North Star-1c: the Blender side of one global step (no-render preflight, the step's ONE acquisition, rehearsal).

Contract: docs/north-star/ns1c-coherent-first-scene-switch-contract.md, section 15.  Normally run through
``ns1c_run.py`` (``preflight`` / ``acquire`` of a step):

    blender -b scenes/classroom/classroom_eye.blend --python-exit-code 1 \
        -P tools/north_star/ns1c_render.py -- --mode preflight --step-dir RUN/steps/step-NN
    blender -b scenes/classroom/classroom_eye.blend --python-exit-code 1 \
        -P tools/north_star/ns1c_render.py -- --mode canonical --step-dir RUN/steps/step-NN
    blender -b --factory-startup --python-exit-code 1 \
        -P tools/north_star/ns1c_render.py -- --mode rehearsal --step-dir DEV_RUN/steps/step-NN --spp 16

A thin driver over the accepted acquisition helpers, imported read-only: ``ab1a_render`` (``calibration``,
``acquire_pair``, ``write_json``, ``new_dir``) and the accepted NS1a driver ``ns1a_render`` (``eye_pose``,
``configure_and_check``, ``check_record``, ``exr_samples``, ``Budget``, ``build_rehearsal_scene``), exactly as NS1b's
``ns1b_render``.  The gaze is the H0 world gaze of the step's ONE scheduled action (``plan/decision.json``); the head is
the fixed AB1a head.  The calibration built here must be byte-identical to the host-planned one.  The instance catalog
is written sealed, serialized exactly as NS1a's sealed document, and its seal must equal NS1a's before anything is
rendered.  Every failure exits nonzero.
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
for _p in (HERE.parent / "active_bootstrap", HERE.parent, HERE):
    sys.path.insert(0, str(_p))

import ab1a_render as AR  # noqa: E402  (accepted AB1a Blender acquisition helpers, read-only)
import ns1a_render as NR  # noqa: E402  (accepted NS1a Blender driver helpers, read-only)
import ns1c_spec as SP  # noqa: E402

PREFIX = "[ns1c-render]"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def calib_bytes(c: dict) -> bytes:
    return (json.dumps(c, indent=1, sort_keys=True, allow_nan=False) + "\n").encode()


def the_action(sd: Path) -> tuple[dict, bytes]:
    """The step's ONE scheduled action and its host-planned calibration bytes."""
    d = json.loads((sd / "plan/decision.json").read_text())
    act = d.get("action")
    if d.get("kind") != "attend" or not act:
        raise RuntimeError(f"STOP the step has no scheduled action (kind {d.get('kind')})")
    plan = (sd / "plan/planned-calibration.json").read_bytes()
    if hashlib.sha256(plan).hexdigest() != act["planned_calibration_sha256"]:
        raise RuntimeError("STOP the planned calibration differs from the decision")
    return act, plan


def build_calibration(sd: Path, pose: dict, strict: bool) -> tuple[dict, dict, dict]:
    act, plan = the_action(sd)
    y, p = (float(v) for v in act["world_gaze_deg"])
    c = AR.calibration(y, p, pose)
    b = calib_bytes(c)
    rep = {"world_gaze_deg": [y, p], "local_gaze_deg": act["local_gaze_deg"], "target": act["target"],
           "calibration_max_abs_diff_from_planned": AR.calib_diff(json.loads(plan), json.loads(b)),
           "byte_identical_to_planned": b == plan, "calibration_sha256": hashlib.sha256(b).hexdigest()}
    if strict and not rep["byte_identical_to_planned"]:
        raise RuntimeError("STOP BEFORE RENDERING: the calibration built from the EYE is not the planned one "
                           + json.dumps(rep, sort_keys=True))
    return act, c, rep


def preflight(a) -> None:
    import bpy
    sd = Path(a.step_dir).resolve()
    out = sd / "preflight"
    if (out / "preflight.json").exists():
        raise FileExistsError(f"STOP {out / 'preflight.json'} exists: the step's preflight runs once")
    out.mkdir(parents=True, exist_ok=True)
    pose = NR.eye_pose(strict=True)
    act, c, rep = build_calibration(sd, pose, strict=True)
    cfg = NR.configure_and_check(c, SP.SPP, True, 0)
    AR.write_json(out / "preflight.json", {
        "schema": "NS1c-preflight-v1", "truth": SP.TRUTH_DERIVED,
        "statement": "Classroom loaded and configured at 4096 spp for the step's ONE scheduled gaze; EYE pose, calibration "
                     "and settings checked against the accepted records; NO render",
        "blend": bpy.data.filepath, "blend_realpath": os.path.realpath(bpy.data.filepath),
        "blender": bpy.app.version_string, "eye_pose": pose, "spp": SP.SPP, "gaze_H0_deg": rep["world_gaze_deg"],
        "target": act["target"], "global_step": act["global_step"], "calibration_identity": rep, **cfg,
        "rendered": False})
    print(f"{PREFIX} COMPLETE preflight (no render)", flush=True)


def acquisition(sd: Path, spp: int, strict: bool, extra_record: dict) -> dict:
    """The step's ONE binocular observation at the scheduled H0 gaze (canonical and rehearsal use this path)."""
    import classroom_oracle1_render as CO
    import render_foveated as RF
    obs = sd / "observation"
    if obs.exists() and any(obs.iterdir()):
        raise FileExistsError(f"STOP {obs} exists: a step's physical observation is never re-rendered")
    pose = NR.eye_pose(strict=True)
    act, c, rep = build_calibration(sd, pose, strict=strict)
    ev = AR.new_dir(obs / "evaluation_only")
    by_id, _by_name = CO._assign_instance_ids()          # the Object Index oracle mechanism (unchanged)
    AR.write_json(ev / "instance-catalog.json", {      # serialized exactly as NS1a's sealed document
        "schema": "NS1a-instance-catalog-v1", "truth": SP.TRUTH_REFERENCE,
        "statement": "SEALED until the NS1a seed freeze: opened only by `evaluate`",
        "instances": [{"instance_id": int(k), "object_name": v} for k, v in sorted(by_id.items())]})
    seal = sha256(ev / "instance-catalog.json")
    if strict and seal != SP.NS1A_CATALOG_SEAL:
        raise RuntimeError(f"STOP BEFORE RENDERING: the Object Index assignment differs from NS1a's (seal {seal})")
    budget = NR.Budget(2, SP.RENDER_BUDGET_S)
    original = RF.render_fixation

    def timed(scene, spp_, out_path=None, seed=0):
        s = original(scene, spp_, out_path, seed=seed)
        budget.eye_done(s)
        return s

    RF.render_fixation = timed                           # in-process timing wrapper only; the accepted file is unchanged
    try:
        acq = AR.new_dir(obs / "acquisition")
        aid = AR.new_dir(obs / "oracle_aid")
        rec = AR.acquire_pair(c, acq, aid, spp, {
            "experiment": SP.EXPERIMENT,
            "action_source": f"NS1c global step {act['global_step']}: {act['source']} proposal of entity "
                             f"{act['target']} in its policy chart, executed at its H0 world gaze",
            "target": act["target"], "global_step": act["global_step"], "local_gaze_deg": act["local_gaze_deg"],
            "world_gaze_deg": act["world_gaze_deg"], "eye_pose": pose, "canonical": bool(strict), "fixed_head": True,
            "calibration_max_abs_diff_from_planned": rep["calibration_max_abs_diff_from_planned"],
            "oracle_aid_dir": "oracle_aid", "product_domains": {
                "acquisition": "INFERENCE / SENSORY: calibration.json, rgb-observation.npz",
                "oracle_aid": "ORACLE AID (ORACLE INPUT): raw_L.exr, raw_R.exr, reference-observation.npz"},
            **extra_record})
        cfg = NR.check_record(rec, strict, 0)
    finally:
        RF.render_fixation = original
    if sha256(acq / "calibration.json") != rep["calibration_sha256"]:
        raise RuntimeError("the written calibration differs from the verified one")
    out = {"schema": "NS1c-acquisition-run-v1", "truth": SP.TRUTH_ORACLE, "experiment": SP.EXPERIMENT,
           "statement": "the step's ONE binocular observation at the H0 world gaze of the scheduled action; the same "
                        "fixed head; static scene; split at once into INFERENCE / SENSORY and ORACLE AID",
           "blend": __import__("bpy").data.filepath, "blender": __import__("bpy").app.version_string,
           "spp": int(spp), "gaze_H0_deg": rec["gaze_yaw_pitch_deg"], "local_gaze_deg": act["local_gaze_deg"],
           "target": act["target"], "global_step": act["global_step"],
           "render_seconds_lr": rec["render_seconds_lr"], "device": rec["device"],
           "calibration_sha256": sha256(acq / "calibration.json"),
           "rgb_observation_sha256": sha256(acq / "rgb-observation.npz"),
           "reference_observation_sha256": sha256(aid / "reference-observation.npz"),
           "exr_samples_lr": {s: NR.exr_samples(aid / f"raw_{s}.exr") for s in ("L", "R")},
           "configuration": cfg, "calibration_identity": rep,
           "catalog_seal": {"path": SP.CATALOG_REL, "sha256": seal, "instances": len(by_id),
                            "equals_ns1a_seal": seal == SP.NS1A_CATALOG_SEAL,
                            "statement": "the id -> name catalog is sealed; no NS1c stage opens it"},
           "budget": budget.record(), **extra_record}
    AR.write_json(sd / SP.ACQ_RUN_REL, out)
    return out


def canonical(a) -> None:
    sd = Path(a.step_dir).resolve()
    rec = acquisition(sd, SP.SPP, strict=True, extra_record={"observation_quality": {
        "spp": SP.SPP, "statement": "the accepted North-Star observation standard (NS1a / NS1b)"}})
    print(f"{PREFIX} COMPLETE canonical " + json.dumps({"gaze_H0_deg": rec["gaze_H0_deg"], "budget": rec["budget"]},
                                                       sort_keys=True), flush=True)


def rehearsal(a) -> None:
    sd = Path(a.step_dir).resolve()
    spp = int(a.spp)
    if spp >= SP.SPP:
        raise ValueError("the rehearsal is a low-spp plumbing run")
    NR.build_rehearsal_scene()
    rec = acquisition(sd, spp, strict=False, extra_record={"rehearsal": True,
                                                           "scene": "synthetic factory-startup room (never Classroom)"})
    print(f"{PREFIX} COMPLETE rehearsal " + json.dumps({"gaze_H0_deg": rec["gaze_H0_deg"], "budget": rec["budget"]},
                                                       sort_keys=True), flush=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mode", required=True, choices=("preflight", "canonical", "rehearsal"))
    ap.add_argument("--step-dir", required=True)
    ap.add_argument("--spp", type=int, default=None)
    a = ap.parse_args(AR.args_after_dashes())
    if (a.mode == "rehearsal") != (a.spp is not None):
        raise ValueError("--spp is a rehearsal option only, and the rehearsal requires it")
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
