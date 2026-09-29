#!/usr/bin/env python3
"""Controller-01B: exactly one post-watchdog continuation look for object 210.

    .venv/bin/python tools/controller/controller01b.py run    --source S --audit A --out O
    .venv/bin/python tools/controller/controller01b.py check  --source S --audit A --out O
    .venv/bin/python tools/controller/controller01b.py visual --source S --audit A --out O --visuals V

Contract: docs/controller/controller-01b-single-continuation-contract.md.

``run`` reconstructs the final causal state of the accepted Controller-01 run from its
controller-time artifacts, reproduces the accepted Controller-01A terminal probe, executes
exactly one OBSERVE (object 210, the reproduced FSG6f proposal, global index 141, local step 24)
through the unchanged ``ClassroomController01.observe``, and re-probes with the unchanged local
policy without executing the result.  ``check`` re-executes the same accepted code path with the
render step replaced by a replay of the saved acquisition, and compares everything with the
recorded run.  ``visual`` writes the Level-A overview.  All modes run under the truth firewall.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
import tempfile
import time

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import fov3d  # noqa: F401
from fov3d.control import frontier, integrated as ic, object_policy
from fov3d.experiments.classroom_oracle import controller01 as c01, epistemic, matcher
from fov3d.reconstruction import surface_map
from fov3d.reconstruction.measurement_memory import valid_patch_measurements

OBJ, GLOBAL_INDEX, LOCAL_STEP = 210, 141, 24
SCHEMA = "Controller01B-run-v1"
ACCEPTED = {"manifest.json": "d293a98fd6bb285e882186af8fbeadba29ab1d1d62efea23f3ed0ff5c62c0e91",
            "actions.json": "12cdbe4d760cce6c494075e4368f9424805b51b997b8b21724bf87f71cc55afd"}
EXPECTED_PRE = {"revision": [24, 1774969], "effective_points": 1938913, "state": "ACTIONABLE", "source": "fsg6f",
                "reason": "continue", "counts": [350, 52, 28, 270], "candidates": 1, "consensus_rejected": 2,
                "gaze": [7.6, 18.2]}
MARKERS = {"QUIET": "CONTROLLER01B_ONE_LOOK_REPROBE_QUIET", "ACTIONABLE": "CONTROLLER01B_ONE_LOOK_REPROBE_ACTIONABLE"}
COUNT_KEYS = ("frontier_raw_count", "frontier_open_count", "frontier_map_resolved_count", "frontier_boundary_resolved_count")
PREFIX = "[controller01b]"


class Gate(RuntimeError):
    pass


RESULTS: list[dict] = []


def gate(name: str, ok: bool, detail: str = "", *, hard: bool = True) -> bool:
    RESULTS.append({"check": name, "ok": bool(ok), "detail": detail})
    print(f"{PREFIX} {'PASS' if ok else 'FAIL'} {name}{'' if ok or not detail else ': ' + detail}")
    if not ok and hard:
        raise Gate(f"{name}: {detail}")
    return bool(ok)


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def npz(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as z:
        return {k: z[k] for k in z.files}


def same_patch(rec: dict, patch: dict) -> bool:
    return (np.array_equal(np.asarray(rec["xyz_h"], np.float32), patch["xyz_h"], equal_nan=True)
            and np.array_equal(np.asarray(rec["valid"], bool), patch["valid"])
            and np.array_equal(np.asarray(rec["instance_id"], np.int32), patch["instance_id"]))


def probe_record(run: c01.ClassroomController01, res: ic.ProbeResult) -> dict:
    dec = run.decisions.get(OBJ, {})
    sel = (dec.get("fsg6f_decision") or {}).get("selected")
    return {
        "state": res.state.value,
        "source": None if res.action is None else res.action.source,
        "proposed_gaze_deg": None if res.action is None else list(res.action.gaze_yaw_pitch_deg),
        "revision": list(run.revision(OBJ)),
        "summary": c01._jsonable(dict(res.detail)),
        "fsg6f_selected": None if sel is None else c01._jsonable({k: sel[k] for k in (
            "yaw_deg", "pitch_deg", "frontier_support_count", "raw_frontier_support_count", "map_resolved_support_count",
            "boundary_resolved_support_count", "frontier_score", "predicted_new_angular_area_deg2")}),
    }


# ---------------------------------------------------------------- reconstruction

def reconstruct(source: Path, out_root: Path) -> tuple[c01.ClassroomController01, list[dict]]:
    """The final causal state of the accepted run, rebuilt into the unchanged adapter class."""
    manifest = json.loads((source / "manifest.json").read_text())
    seeds_doc = json.loads((source / "bootstrap/seeds.json").read_text())
    catalog_doc = json.loads((source / "bootstrap/instance_catalog.json").read_text())
    actions = json.loads((source / "actions.json").read_text())["actions"]
    scene = Path(manifest["scene"]) if Path(manifest["scene"]).is_absolute() else REPO / manifest["scene"]
    args = argparse.Namespace(blender="blender", profile=manifest["profile"], device=manifest["device"],
                              spp=manifest["spp_override"])
    run = c01.ClassroomController01(REPO, out_root, scene, args, seeds_doc, catalog_doc)
    ctx = run.ctx[OBJ]
    bad_add, bad_patch, own = [], [], 0
    for a in actions:
        i, k, s = int(a["target_id"]), int(a["object_local_step"]), int(a["global_step"])
        patch = npz(source / f"objects/instance_{i:04d}/patches/fix_{k:02d}.npz")
        added, _head = run.remember_measurements(patch, s, i)
        if {str(x): int(v) for x, v in sorted(added.items())} != a["measurement_memory_additions"]:
            bad_add.append(s)
        adir = source / f"objects/instance_{i:04d}/acquisitions/fix_{k:02d}"
        c = json.loads((adir / "calibration.json").read_text())
        rec, _meta, st = matcher.compute(c, npz(adir / "oracle_observation.npz"))
        if not same_patch(rec, patch):
            bad_patch.append(s)
        epistemic.add_observation(run.seen, c, st["ids_left"], st["raw_support_L"], st["ids_right"],
                                  st["raw_support_R"], rec["valid"], i)
        if i == OBJ:
            own += 1
            tp = int((np.asarray(rec["valid"], bool) & (np.asarray(rec["instance_id"]) == OBJ)).sum())
            p = surface_map.Patch(patch_id=f"fix_{k:02d}", xyz_h=rec["xyz_h"], rgb=rec["rgb_left"],
                                  instance_id=rec["instance_id"])
            if ctx.surface_map is None:
                if tp < c01.public.MIN_INITIAL_TARGET_POINTS:
                    raise Gate("210's seed look cannot initialize its map")
                ctx.surface_map = surface_map.initialize(p, OBJ)
            elif tp >= c01.public.MIN_INITIAL_TARGET_POINTS:
                ctx.surface_map, _m = surface_map.fuse(ctx.surface_map, p, OBJ, float(c01.public.FUSION["association_radius_m"]),
                                                       float(c01.public.FUSION["hash_cell_m"]))
            gaze = (float(a["gaze_deg"][0]), float(a["gaze_deg"][1]))
            epistemic.add_observation(ctx.evidence, c, st["ids_left"], st["raw_support_L"], st["ids_right"],
                                      st["raw_support_R"], rec["valid"], OBJ)
            ctx.history.append(object_policy.history_entry(
                calibration=c, instance_L=st["ids_left"], raw_support_L=st["raw_support_L"],
                instance_R=st["ids_right"], raw_support_R=st["raw_support_R"], target_object_id=OBJ))
            ctx.visited.append(gaze)
            ctx.gaze, ctx.calibration, ctx.state = gaze, c, st
    run.current_step = int(actions[-1]["global_step"])
    gate("reconstruction: all 141 replayed per-action memory additions equal the logged ones", not bad_add, str(bad_add[:5]))
    gate("reconstruction: all 141 matcher-recreated patches equal the saved patches", not bad_patch, str(bad_patch[:5]))
    gate("reconstruction: 210 has 24 own looks", own == 24 == int(manifest["final_service_states"][str(OBJ)]["fixations"]))
    final = npz(source / f"objects/instance_{OBJ:04d}/final_map.npz")
    sm = ctx.surface_map
    gate("reconstruction: 210's replayed active map equals the saved final_map (xyz, rgb, ids, support, provenance)",
         np.array_equal(np.asarray(sm.xyz_h).astype(np.float32), final["xyz_h"]) and np.array_equal(np.asarray(sm.rgb), final["rgb"])
         and np.array_equal(np.asarray(sm.instance_id), final["instance_id"])
         and np.array_equal(np.asarray(sm.support_count), final["support_count"])
         and np.array_equal(np.asarray(sm.provenance_mask), final["provenance_mask"])
         and list(sm.patch_ids) == [f"fix_{k:02d}" for k in range(24)], f"{len(sm.xyz_h)} surfels")
    # The other localized objects are never probed or observed here.  Their saved final active maps
    # enter only the scene support layers of E_t(210) (validated against the saved terminal view).
    for o in manifest["objects"]:
        i = int(o["instance_id"])
        if i != OBJ:
            z = npz(source / f"objects/instance_{i:04d}/final_map.npz")
            run.ctx[i].surface_map = surface_map.SurfaceMap(np.asarray(z["xyz_h"], np.float64), z["rgb"], z["instance_id"],
                                                            z["support_count"], z["provenance_mask"], [])
    return run, actions


def validate_pre(run: c01.ClassroomController01, source: Path, audit: dict) -> tuple[ic.ProbeResult, dict]:
    view = run.save_view(OBJ, run.current_step, "pre_action")
    saved = npz(source / f"objects/instance_{OBJ:04d}/epistemic/final_terminal.npz")
    mine = npz(run.root / view["path"])
    gate("M_t: E_t(210) from the reconstructed memory equals the saved Controller-01 terminal view",
         np.array_equal(mine["class_code"], saved["class_code"]) and np.array_equal(mine["region_code"], saved["region_code"]),
         f"{int((mine['class_code'] != saved['class_code']).sum())} cells differ")
    diag = json.loads((source / f"objects/instance_{OBJ:04d}/epistemic/final_terminal.json").read_text())["diag"]
    gate("M_t: global head-evidence depth cells and seen_any cells equal the saved terminal view's",
         int(run.head.depth_seen.sum()) == diag["head_depth_cells"] and int(run.seen.seen_any.sum()) == diag["eye_ray_seen_cells"],
         f"{int(run.head.depth_seen.sum())}/{diag['head_depth_cells']}, {int(run.seen.seen_any.sum())}/{diag['eye_ray_seen_cells']}")
    res = run.probe(OBJ)
    rec = probe_record(run, res)
    term = audit["terminal_probe"]
    f = rec["summary"]["fsg6f"]
    ok = (rec["state"] == EXPECTED_PRE["state"] == term["state"] and rec["source"] == EXPECTED_PRE["source"] == term["source"]
          and rec["revision"] == EXPECTED_PRE["revision"] == term["revision"]
          and rec["summary"]["effective_points"] == EXPECTED_PRE["effective_points"] == term["effective_points"]
          and f["reason"] == EXPECTED_PRE["reason"] and [f[k] for k in COUNT_KEYS] == EXPECTED_PRE["counts"]
          and f["candidates"] == EXPECTED_PRE["candidates"] and f["consensus_rejected_candidates"] == EXPECTED_PRE["consensus_rejected"]
          and all(abs(rec["proposed_gaze_deg"][j] - EXPECTED_PRE["gaze"][j]) < 1e-9 for j in (0, 1))
          and rec["summary"] == term["summary"])
    # 01A evaluated the probe on the saved float32 map; here the map is the exact float64 replay of the accepted
    # fusion (the runtime representation).  Discrete fields must match exactly; the two float descriptors of
    # the selected candidate may differ only at float32 rounding level, and the deltas are recorded.
    sel_r, sel_t = rec["fsg6f_selected"], term["fsg6f_selected"]
    floats = ("frontier_score", "predicted_new_angular_area_deg2")
    ok_sel = sel_r is not None and sel_t is not None and all(sel_r[k] == sel_t[k] for k in sel_r if k not in floats) \
        and all(abs(sel_r[k] - sel_t[k]) <= 1e-5 * max(1.0, abs(sel_t[k])) for k in floats)
    rec["selected_float_deltas_vs_01A"] = {k: float(sel_r[k] - sel_t[k]) for k in floats} if ok_sel else None
    gate("pre-action probe reproduces the accepted 01A terminal probe (ACTIONABLE, FSG6f continue, 350/52/28/270, "
         "1 candidate, [7.6, 18.2], effective 1,938,913)", ok and ok_sel,
         f"{rec['state']} {f} {rec['proposed_gaze_deg']} {rec['revision']} selected {sel_r} vs {sel_t}")
    return res, rec


@contextmanager
def replay_renderer(saved_run: Path):
    """Replace the Blender call inside the unchanged observe() by a copy of the saved acquisition."""
    original = c01._run

    def fake(cmd, log, cwd):
        out = Path(cmd[cmd.index("--out") + 1])
        rel = out.relative_to(out.parents[3])
        src = saved_run / rel
        for name in ("calibration.json", "oracle_observation.npz", "acquisition.json"):
            shutil.copyfile(src / name, out / name)
        Path(log).write_text("replayed saved acquisition (no render)\n")
    c01._run = fake
    try:
        yield
    finally:
        c01._run = original


# ---------------------------------------------------------------- run

def cmd_run(a) -> int:
    source, out = a.source.resolve(), a.out.resolve()
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"output must be new or empty: {out}")
    out.mkdir(parents=True, exist_ok=True)
    fw = ic.TruthFirewall(source, c01.is_evaluation_truth)
    record: dict = {"schema": SCHEMA, "contract": "docs/controller/controller-01b-single-continuation-contract.md",
                    "source_run": str(source), "source_audit": str(a.audit.resolve()), "observations_executed": 0}
    t0 = time.perf_counter()
    try:
        with fw:
            for name, digest in ACCEPTED.items():
                gate(f"source {name} is the accepted artifact", sha(source / name) == digest)
            record["source_hashes"] = {n: sha(source / n) for n in ACCEPTED}
            audit = json.loads(a.audit.read_text())
            gate("source audit is the accepted Controller-01A result", audit.get("outcome") == "FINAL_REPROBE_ACTIONABLE"
                 and audit.get("failure") is None)
            run, actions = reconstruct(source, out)
            t_rec = time.perf_counter() - t0
            pre_res, pre = validate_pre(run, source, audit)
            record["pre_probe"] = pre
            action = pre_res.action
            gate("the one action: target 210, FSG6f proposal [7.6, 18.2], fixed vergence/focus",
                 action is not None and action.target_id == OBJ and action.source == "fsg6f"
                 and dict(action.vergence) == c01.VERGENCE and dict(action.focus) == c01.FOCUS)
            before = {"active_map": len(run.map_xyz(OBJ)), "effective": len(run.geometry(OBJ)),
                      "measured": dict(run.measured_points), "depth_cells": int(run.head.depth_seen.sum()),
                      "seen_cells": int(run.seen.seen_any.sum())}
            # ---- the ONE new sensory action
            outcome = run.observe(GLOBAL_INDEX, action, LOCAL_STEP)
            record["observations_executed"] = 1
            row = run.trajectory[OBJ][-1]
            post_res = run.probe(OBJ)
            post = probe_record(run, post_res)
            run.save_view(OBJ, GLOBAL_INDEX, "post_action")
            adir = out / f"objects/instance_{OBJ:04d}/acquisitions/fix_{LOCAL_STEP:02d}"
            cal = json.loads((adir / "calibration.json").read_text())
            acq = json.loads((adir / "acquisition.json").read_text())
            added = outcome.record["measurement_memory_additions"]
            record.update({
                "action": {"type": "OBSERVE", "target_id": action.target_id, "gaze_deg": list(action.gaze_yaw_pitch_deg),
                           "source": action.source, "vergence": dict(action.vergence), "focus": dict(action.focus),
                           "global_index": GLOBAL_INDEX, "local_step": LOCAL_STEP},
                "calibration": {"gaze_yaw_pitch_deg": cal["gaze_yaw_pitch_deg"],
                                "prescribed_vergence_distance_m": cal["prescribed_vergence_distance_m"],
                                "profile": cal["profile"], "render_seeds_lr": acq["render_seeds_lr"], "spp": acq["spp"],
                                "device": acq["device"]},
                "measurements": {
                    **{k: outcome.record[k] for k in ("target_valid_points", "all_instance_valid_points",
                                                      "active_map_size_before", "active_map_size_after", "new_surfels",
                                                      "nonnew_target_points", "empty_look", "head_evidence",
                                                      "render_seconds", "prescribed_vergence_distance_m")},
                    "measured_instance_ids": sorted(int(k) for k in added),
                    "memory_additions_by_instance": added,
                    "memory_additions_total": int(sum(added.values())),
                    "memory_additions_to_210": int(added.get(str(OBJ), 0)),
                    "fusion": c01._jsonable(row["fusion"]),
                    "effective_before": before["effective"], "effective_after": len(run.geometry(OBJ)),
                    "active_map_before": before["active_map"], "active_map_after": len(run.map_xyz(OBJ)),
                    "head_depth_cells_before": before["depth_cells"], "head_depth_cells_after": int(run.head.depth_seen.sum()),
                    "seen_any_cells_before": before["seen_cells"], "seen_any_cells_after": int(run.seen.seen_any.sum()),
                    "incidental_instance_ids_seen": sorted(int(k) for k in run.incidental[OBJ]),
                },
                "post_probe": post,
                "timing_s": {"reconstruction": round(t_rec, 2), "total": round(time.perf_counter() - t0, 2)},
            })
    except Gate as exc:
        record["failure"] = str(exc)
    record["truth_firewall"] = {"violations": list(fw.violations), "opened_source_files": sorted(fw.opened)}
    record["checks"] = RESULTS
    ok = "failure" not in record and not fw.violations and record.get("observations_executed") == 1
    record["outcome"] = post["state"] if ok else None
    record["marker"] = MARKERS[post["state"]] if ok else None
    (out / "continuation.json").write_text(json.dumps(c01._jsonable(record), indent=1, sort_keys=True) + "\n")
    (out / "manifest.json").write_text(json.dumps({"schema": SCHEMA, "control_complete": ok, "marker": record["marker"],
                                                   "source_run": str(source)}, indent=1) + "\n")
    if not ok:
        print(f"{PREFIX} FAILURE: {record.get('failure') or fw.violations} (no marker)")
        return 1
    m = record["measurements"]
    print(f"{PREFIX} look 25: target-valid {m['target_valid_points']}, new surfels {m['new_surfels']}, active map "
          f"{m['active_map_before']} -> {m['active_map_after']}, effective {m['effective_before']} -> {m['effective_after']}")
    f = post["summary"]["fsg6f"]
    print(f"{PREFIX} post-look probe: {post['state']} source={post['source']} gaze={post['proposed_gaze_deg']} "
          f"fsg6f={f} cyclopean={post['summary']['cyclopean']}")
    print(f"{PREFIX} RESULT {record['marker']}")
    return 0


# ---------------------------------------------------------------- check

def recompute(source: Path, saved: Path, audit: dict, work: Path) -> tuple[dict, dict, c01.ClassroomController01, dict]:
    run, _actions = reconstruct(source, work)
    pre_res, pre = validate_pre(run, source, audit)
    pre_state = {"map": np.asarray(run.map_xyz(OBJ)).copy(), "geometry": run.geometry(OBJ),
                 "ctx_gaze": run.ctx[OBJ].gaze}
    with replay_renderer(saved):
        outcome = run.observe(GLOBAL_INDEX, pre_res.action, LOCAL_STEP)
    post_res = run.probe(OBJ)
    return pre, {"outcome": outcome, "post": probe_record(run, post_res), "row": run.trajectory[OBJ][-1]}, run, pre_state


def cmd_check(a) -> int:
    source, out = a.source.resolve(), a.out.resolve()
    record = json.loads((out / "continuation.json").read_text())
    audit = json.loads(a.audit.read_text())
    fw = ic.TruthFirewall(source, c01.is_evaluation_truth)
    failures = 0  # soft-gate failures (also recorded in RESULTS)
    try:
        with fw, tempfile.TemporaryDirectory() as tmp:
            soft = lambda n, ok, d="": gate(n, ok, d, hard=False)  # noqa: E731
            ok_src = all(sha(source / n) == d for n, d in ACCEPTED.items()) and record.get("source_hashes") == ACCEPTED
            failures += not soft("1 source run is the accepted Controller-01 run (hashes, recorded and live)", ok_src)
            if not ok_src:
                raise Gate("wrong source run")
            pre, post, run, _ = recompute(source, out, audit, Path(tmp))
            failures += not soft("2 recorded pre-action probe equals the recomputed one and the accepted 01A terminal probe",
                                 record["pre_probe"] == pre and record["pre_probe"]["summary"] == audit["terminal_probe"]["summary"])
            act = record["action"]
            acqs = sorted(p.relative_to(out).as_posix() for p in out.glob("objects/*/acquisitions/*") if p.is_dir())
            patches = sorted(p.relative_to(out).as_posix() for p in out.glob("objects/*/patches/*.npz"))
            failures += not soft("3 target is 210 and the only acquisition is objects/instance_0210",
                                 act["target_id"] == OBJ and acqs == [f"objects/instance_{OBJ:04d}/acquisitions/fix_{LOCAL_STEP:02d}"],
                                 str(acqs))
            cal = json.loads((out / acqs[0] / "calibration.json").read_text()) if acqs else {}
            failures += not soft("4 gaze equals the reproduced proposal [7.6, 18.2] in the record and the acquisition",
                                 act["gaze_deg"] == pre["proposed_gaze_deg"] and act["source"] == pre["source"] == "fsg6f"
                                 and all(abs(act["gaze_deg"][j] - EXPECTED_PRE["gaze"][j]) < 1e-9 for j in (0, 1))
                                 and cal.get("gaze_yaw_pitch_deg") == act["gaze_deg"], str(act["gaze_deg"]))
            snap = run.memory.snapshot(OBJ)
            n210 = int(post["outcome"].record["measurement_memory_additions"].get(str(OBJ), 0))
            last = snap.source_global_index[len(snap.source_global_index) - n210:]
            failures += not soft("5 global index 141 and local step 24 (record, patch path, memory provenance)",
                                 act["global_index"] == GLOBAL_INDEX and act["local_step"] == LOCAL_STEP
                                 and patches == [f"objects/instance_{OBJ:04d}/patches/fix_{LOCAL_STEP:02d}.npz"]
                                 and bool(np.all(last == GLOBAL_INDEX))
                                 and bool(np.all(snap.source_global_index[:len(snap.source_global_index) - n210] <= 140)),
                                 str(patches))
            failures += not soft("6 vergence 2.10 m fixed and depth of field disabled (record and calibration)",
                                 act["vergence"] == c01.VERGENCE and act["focus"] == c01.FOCUS
                                 and abs(float(cal.get("prescribed_vergence_distance_m", -1)) - 2.10) < 1e-12
                                 and record["measurements"]["prescribed_vergence_distance_m"] == 2.1)
            failures += not soft("7 truth firewall: no violation in the run record or this check",
                                 record["truth_firewall"]["violations"] == [] and not fw.violations)
            saved_patch = npz(out / f"objects/instance_{OBJ:04d}/patches/fix_{LOCAL_STEP:02d}.npz")
            _xyz, ids, _m = valid_patch_measurements(saved_patch)
            by = {str(int(i)): int((ids == i).sum()) for i in np.unique(ids)}
            failures += not soft("8 all valid positive-instance measurements appended (saved patch = record = re-executed)",
                                 by == record["measurements"]["memory_additions_by_instance"]
                                 == post["outcome"].record["measurement_memory_additions"], str(by))
            post_map = npz(out / f"objects/instance_{OBJ:04d}/maps/fix_{LOCAL_STEP:02d}.npz")
            sm = run.ctx[OBJ].surface_map
            failures += not soft("9 no incidental point fused into 210's active map (all surfel ids are 210)",
                                 bool(np.all(post_map["instance_id"] == OBJ)))
            failures += not soft("10 post-look active map equals the accepted 12 mm fusion re-executed on the saved look",
                                 np.array_equal(np.asarray(sm.xyz_h).astype(np.float32), post_map["xyz_h"])
                                 and np.array_equal(np.asarray(sm.support_count), post_map["support_count"])
                                 and np.array_equal(np.asarray(sm.provenance_mask), post_map["provenance_mask"])
                                 and record["measurements"]["new_surfels"] == post["outcome"].record["new_surfels"]
                                 and record["measurements"]["active_map_after"] == len(post_map["xyz_h"]))
            failures += not soft("11 exactly one new OBSERVE (one acquisition, one patch, one recorded observation)",
                                 len(acqs) == 1 and len(patches) == 1 and record["observations_executed"] == 1)
            want = MARKERS[post["post"]["state"]]
            failures += not soft("12 recorded post-look state and marker equal the re-executed post-look probe",
                                 record["post_probe"] == post["post"] and record["outcome"] == post["post"]["state"]
                                 and record["marker"] == want, f"{record['marker']} vs {want}")
    except Gate as exc:
        print(f"{PREFIX} CHECK STOPPED: {exc}")
    except Exception as exc:  # noqa: BLE001
        print(f"{PREFIX} CHECK ERROR: {type(exc).__name__}: {exc}")
        RESULTS.append({"check": "check completed without error", "ok": False, "detail": f"{type(exc).__name__}: {exc}"})
    if fw.violations:
        RESULTS.append({"check": "check-mode truth firewall", "ok": False, "detail": str(fw.violations)})
    bad = sum(not r["ok"] for r in RESULTS)
    print(f"{PREFIX} SUMMARY checked={len(RESULTS)} failed={bad}")
    return 1 if bad else 0


# ---------------------------------------------------------------- visual

SURFACE, INK, INK2, OLD_PTS = (252, 252, 251), (11, 11, 11), (82, 81, 78), (178, 176, 170)
BLUE, ORANGE, AQUA = (42, 120, 214), (235, 104, 52), (27, 175, 122)
BADGE = {"CONTROLLER-TIME": (42, 120, 214), "DERIVED": (82, 81, 78)}


def font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def angles(xyz):
    p = np.asarray(xyz, np.float64).reshape(-1, 3)
    return np.degrees(np.arctan2(p[:, 0], -p[:, 2])), np.degrees(np.arctan2(p[:, 1], np.hypot(p[:, 0], p[:, 2])))


class Chart:
    def __init__(self, y0, y1, p0, p1, width):
        self.y0, self.y1, self.p0, self.p1 = y0, y1, p0, p1
        self.s = width / (y1 - y0)
        self.w, self.h = int(round(width)), int(round((p1 - p0) * self.s))

    def px(self, yaw, pitch):
        return (np.asarray(yaw, float) - self.y0) * self.s, (self.p1 - np.asarray(pitch, float)) * self.s


def render(ch, xyz, colors, radius=0, img=None):
    out = np.full((ch.h, ch.w, 3), SURFACE, np.uint8) if img is None else img
    xyz = np.asarray(xyz, float).reshape(-1, 3)
    if not len(xyz):
        return out
    yaw, pit = angles(xyz)
    x, y = ch.px(yaw, pit)
    cols = np.broadcast_to(np.asarray(colors, np.uint8), (len(xyz), 3))
    keep = (x >= -3) & (x < ch.w + 3) & (y >= -3) & (y < ch.h + 3)
    x, y, cols, rng = x[keep], y[keep], cols[keep], np.linalg.norm(xyz[keep], axis=1)
    if not len(rng):
        return out
    offs = [(dx, dy) for dx in range(-radius, radius + 1) for dy in range(-radius, radius + 1) if dx * dx + dy * dy <= radius * radius]
    xi = np.concatenate([np.floor(x).astype(np.int64) + dx for dx, _ in offs])
    yi = np.concatenate([np.floor(y).astype(np.int64) + dy for _, dy in offs])
    rr = np.tile(rng, len(offs)); idx = np.tile(np.arange(len(rng)), len(offs))
    ok = (xi >= 0) & (xi < ch.w) & (yi >= 0) & (yi < ch.h)
    flat, rr, idx = yi[ok] * ch.w + xi[ok], rr[ok], idx[ok]
    if not len(flat):
        return out
    order = np.lexsort((rr, flat)); first = np.r_[True, flat[order][1:] != flat[order][:-1]]
    out.reshape(-1, 3)[flat[order[first]]] = cols[idx[order[first]]]
    return out


def marks(img, ch, items):
    im = Image.fromarray(img); d = ImageDraw.Draw(im)
    for m in items:
        x, y = (float(v) for v in ch.px(*m["gaze"]))
        col = m.get("color", INK)
        if m["kind"] == "fov":
            h = 6.0 * ch.s; d.rectangle([x - h, y - h, x + h, y + h], outline=col, width=3)
        elif m["kind"] == "dot":
            r = m.get("r", 5); d.ellipse([x - r, y - r, x + r, y + r], fill=col)
        else:
            r = m.get("r", 9); d.ellipse([x - r, y - r, x + r, y + r], outline=col, width=3)
        if m.get("to"):
            tx, ty = (float(v) for v in ch.px(*m["to"]))
            d.line([x, y, tx, ty], fill=INK, width=3); ang = math.atan2(ty - y, tx - x)
            for s in (0.45, -0.45):
                d.line([tx, ty, tx - 14 * math.cos(ang + s), ty - 14 * math.sin(ang + s)], fill=INK, width=3)
        if m.get("label"):
            f = font(13); tw = d.textlength(m["label"], font=f)
            lx = x + 12 if (m.get("side") != "left" and x + 12 + tw < im.width) or x - 12 - tw < 0 else x - 12 - tw
            y = y + m.get("dy", 0)
            d.rectangle([lx - 3, y - 10, lx + tw + 3, y + 8], fill=(255, 255, 255)); d.text((lx, y - 8), m["label"], fill=col, font=f)
    return np.asarray(im)


def panel(img, title, badge, lines=()):
    im = Image.fromarray(img)
    out = Image.new("RGB", (im.width, im.height + 36 + 22 * len(lines) + 8), SURFACE)
    d = ImageDraw.Draw(out)
    d.text((6, 8), title, fill=INK, font=font(16))
    bw = d.textlength(badge, font=font(12)) + 14
    d.rounded_rectangle([out.width - bw - 6, 8, out.width - 6, 28], radius=4, fill=BADGE[badge])
    d.text((out.width - bw + 1, 11), badge, fill=(255, 255, 255), font=font(12))
    out.paste(im, (0, 36))
    for n, line in enumerate(lines):
        d.text((6, im.height + 44 + 22 * n), line, fill=INK2, font=font(14))
    return out


def labelled(img, label):
    im = Image.fromarray(img); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, d.textlength(label, font=font(14)) + 10, 20], fill=(255, 255, 255)); d.text((4, 2), label, fill=INK, font=font(14))
    return np.asarray(im)


def vstack(*imgs, gap=6):
    w = max(i.shape[1] for i in imgs)
    return np.concatenate([np.pad(i, ((0, gap), (0, w - i.shape[1]), (0, 0)), constant_values=252) for i in imgs])


def hstack(*imgs, gap=8):
    h = max(i.shape[0] for i in imgs)
    return np.concatenate([np.pad(i, ((0, h - i.shape[0]), (0, gap), (0, 0)), constant_values=252) for i in imgs], axis=1)


def legend(items, width):
    im = Image.new("RGB", (width, 26), SURFACE); d = ImageDraw.Draw(im); x = 6
    for col, label in items:
        d.rectangle([x, 7, x + 14, 21], fill=col); d.text((x + 20, 6), label, fill=INK2, font=font(13))
        x += 34 + d.textlength(label, font=font(13))
    return np.asarray(im)


def frontier_state(ctx, geometry, target_gaze):
    fr = frontier.extract_frontier(geometry, ctx.gaze[0], ctx.gaze[1], ctx.calibration)
    st = frontier.classify_frontier_state(fr, geometry, ctx.history)
    support = np.zeros(len(fr["strength"]), bool)
    if target_gaze is not None:
        u = np.array([round((target_gaze[0] - ctx.gaze[0]) / 5.0), round((target_gaze[1] - ctx.gaze[1]) / 5.0)], float)
        if np.linalg.norm(u) > 0:
            u /= np.linalg.norm(u)
            delta = np.c_[fr["target_yaw_deg"] - fr["yaw_deg"], fr["target_pitch_deg"] - fr["pitch_deg"]]
            dn = np.linalg.norm(delta, axis=1); good = dn > 1e-12
            al = np.zeros(len(delta)); al[good] = (delta[good] / dn[good, None]) @ u
            support = (al >= 0.5) & st["open"]
    return {"xyz": fr["xyz_h"], "open": st["open"], "map": st["map_resolved"], "boundary": st["boundary_resolved"],
            "support": support, "counts": [st["raw_count"], st["open_count"], st["map_resolved_count"], st["boundary_resolved_count"]]}


def cmd_visual(a) -> int:
    source, out = a.source.resolve(), a.out.resolve()
    record = json.loads((out / "continuation.json").read_text())
    audit = json.loads(a.audit.read_text())
    vis = a.visuals.resolve()
    fw = ic.TruthFirewall(source, c01.is_evaluation_truth)
    try:
        with fw, tempfile.TemporaryDirectory() as tmp:
            run, _ = reconstruct(source, Path(tmp))
            pre_res, pre = validate_pre(run, source, audit)
            ctx = run.ctx[OBJ]
            looks = list(ctx.visited)
            geo_pre, map_pre_n = run.geometry(OBJ), len(run.map_xyz(OBJ))
            fs_pre = frontier_state(ctx, geo_pre, EXPECTED_PRE["gaze"])
            gate("visual: recomputed pre-look frontier equals the recorded pre-look probe",
                 fs_pre["counts"] == [pre["summary"]["fsg6f"][k] for k in COUNT_KEYS]
                 and int(fs_pre["support"].sum()) == pre["fsg6f_selected"]["frontier_support_count"])
            prev_n = run.measured_points.get(OBJ, 0)
            with replay_renderer(out):
                outcome = run.observe(GLOBAL_INDEX, pre_res.action, LOCAL_STEP)
            post = probe_record(run, run.probe(OBJ))
            gate("visual: re-executed post-look probe equals the recorded one", post == record["post_probe"])
            geo_post = run.geometry(OBJ)
            snap = run.memory.snapshot(OBJ)
            new_pts = np.asarray(snap.xyz_h[prev_n:], np.float64)
            nxt = post["proposed_gaze_deg"]
            fs_post = frontier_state(ctx, geo_post, nxt if post["source"] == "fsg6f" else None)
            gate("visual: recomputed post-look frontier equals the recorded post-look probe",
                 fs_post["counts"] == [post["summary"]["fsg6f"][k] for k in COUNT_KEYS])
            L = cv2.imread(str(out / f"objects/instance_{OBJ:04d}/benchmark/fix_{LOCAL_STEP:02d}_L.png"))[..., ::-1]
            R = cv2.imread(str(out / f"objects/instance_{OBJ:04d}/benchmark/fix_{LOCAL_STEP:02d}_R.png"))[..., ::-1]
            patch = npz(out / f"objects/instance_{OBJ:04d}/patches/fix_{LOCAL_STEP:02d}.npz")
            mem_scene = [np.asarray(run.memory.snapshot(i).xyz_h, np.float64) for i in run.memory.instance_ids()]
    except Gate as exc:
        print(f"{PREFIX} VISUAL REFUSED: {exc}")
        return 1
    m = record["measurements"]
    width = 900
    ch = Chart(-24.0, 31.0, -3.0, 23.5, width)
    gaze = tuple(record["action"]["gaze_deg"])
    # 1. object 210 and the requested fixation
    bg = render(ch, np.concatenate(mem_scene), (214, 212, 206))
    bg = render(ch, geo_pre, OLD_PTS, img=bg)
    items = [{"gaze": g, "kind": "dot", "color": BLUE, "r": 4} for g in looks]
    items += [{"gaze": looks[-1], "kind": "ring", "color": INK, "to": gaze, "label": "look 24 (step 101)", "side": "left",
               "dy": 18},
              {"gaze": gaze, "kind": "fov", "color": ORANGE},
              {"gaze": gaze, "kind": "ring", "color": ORANGE, "label": "look 25: OBSERVE [7.6, 18.2] (step 141)"}]
    if nxt is not None:
        items.append({"gaze": tuple(nxt), "kind": "ring", "color": AQUA, "label": f"next proposal {post['source']} "
                      f"[{nxt[0]:.1f}, {nxt[1]:.1f}] (not executed)"})
    p1 = panel(marks(bg, ch, items), "1. OBJECT 210 wall.008 AND THE REQUESTED FIXATION", "CONTROLLER-TIME",
               ["gray = 210's effective geometry before look 25; blue dots = its 24 earlier own looks",
                "orange box = look 25 (12 deg core), the one observation still requested by the accepted local policy"])
    # 2. the new binocular observation
    Ls = cv2.resize(L, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST).copy()
    Rs = cv2.resize(R, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST)
    mk = cv2.resize((patch["valid"] & (patch["instance_id"] == OBJ)).astype(np.uint8), None, fx=2, fy=2,
                    interpolation=cv2.INTER_NEAREST).astype(bool)
    Ls[mk] = (0.5 * Ls[mk] + 0.5 * np.array(ORANGE)).astype(np.uint8)
    cs, _ = cv2.findContours(mk.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE); cv2.drawContours(Ls, cs, -1, ORANGE, 2)
    p2 = panel(hstack(labelled(Ls, "left eye (rectified core)"), labelled(Rs, "right eye")),
               "2. FOVEATED OBSERVATION: look 25 of 210 (step 141)", "CONTROLLER-TIME",
               [f"orange = {m['target_valid_points']:,} target-valid points of 210; all-instance valid {m['all_instance_valid_points']:,}; "
                f"measured ids {m['measured_instance_ids']}",
                f"render {m['render_seconds']:.1f} s; fixed vergence 2.10 m; depth of field disabled"])

    def fr_img(geo, fs, cur, to, label, proposal=None):
        img = render(ch, geo[:: max(1, len(geo) // 400000)], OLD_PTS)
        cols = np.zeros((len(fs["xyz"]), 3), np.uint8); cols[fs["map"]] = BLUE; cols[fs["boundary"]] = AQUA; cols[fs["open"]] = ORANGE
        img = render(ch, fs["xyz"], cols, radius=2, img=img)
        items = [{"gaze": (float(y), float(p)), "kind": "ring", "color": INK, "r": 5} for y, p in zip(*angles(fs["xyz"][fs["support"]]))]
        items.append({"gaze": cur, "kind": "ring", "color": INK, **({"to": to} if to is not None else {})})
        if proposal is not None:
            items.append({"gaze": proposal[0], "kind": "ring", "color": AQUA, "r": 11, "label": proposal[1]})
        return labelled(marks(img, ch, items), label)
    fpre, fpost = pre["summary"]["fsg6f"], post["summary"]["fsg6f"]
    post_label = (f"after look 25: {post['state']}"
                  + (f", {post['source']} -> [{nxt[0]:.1f}, {nxt[1]:.1f}]" if nxt is not None else "")
                  + f"; OPEN {fpost['frontier_open_count']}, candidates {fpost['candidates']}")
    p3 = panel(vstack(fr_img(geo_pre, fs_pre, looks[-1], gaze, f"before (terminal state): OPEN {fpre['frontier_open_count']}, "
                             f"candidates {fpre['candidates']} -> [7.6, 18.2]"),
                      fr_img(geo_post, fs_post, gaze, tuple(nxt) if post["source"] == "fsg6f" else None, post_label,
                             None if nxt is None else (tuple(nxt), f"post-look proposal ({post['source']})")),
                      legend([(ORANGE, "OPEN"), (BLUE, "MAP_RESOLVED"), (AQUA, "BOUNDARY_RESOLVED"),
                              (INK, "ringed: OPEN support of the selected candidate")], ch.w)),
               "3. EPISTEMIC: FSG6f FRONTIER STATE, before -> after", "DERIVED",
               [f"raw/OPEN/map/boundary {'/'.join(str(fpre[k]) for k in COUNT_KEYS)} -> {'/'.join(str(fpost[k]) for k in COUNT_KEYS)}",
                "recomputed with the accepted frontier functions; counts equal the recorded probes"
                + ("" if post["summary"]["cyclopean"] is None else
                   f"; Cyclopean eligible {post['summary']['cyclopean']['eligible_cells']}")])
    g1 = render(ch, geo_pre, OLD_PTS)
    g2 = render(ch, geo_pre, OLD_PTS)
    g2 = render(ch, new_pts, ORANGE, radius=1, img=g2)
    p4 = panel(vstack(labelled(g1, f"before: effective {m['effective_before']:,} (active map {m['active_map_before']:,})"),
                      labelled(g2, f"after: effective {m['effective_after']:,} (+{m['effective_after'] - m['effective_before']:,}); "
                                   f"active map {m['active_map_after']:,} (+{m['new_surfels']:,} new surfels)"),
                      legend([(OLD_PTS, "effective geometry before look 25"), (ORANGE, f"look-25 measurements of 210 ({len(new_pts):,})")], ch.w)),
               "4. PERSISTENT 3-D MEMORY: EFFECTIVE CAUSAL GEOMETRY, before -> after", "CONTROLLER-TIME",
               [f"new surfels {m['new_surfels']:,}; non-new target points {m['nonnew_target_points']:,}; "
                f"matched-distance median {1000 * m['fusion']['matched_distance_m']['median']:.1f} mm"
                if m["fusion"].get("matched_distance_m") else f"new surfels {m['new_surfels']:,}",
                "fused with the accepted 12 mm rule; no incidental point fused"])
    panels = [p1, p2, p3, p4]
    cw = max(p.width for p in panels); rows = [panels[:2], panels[2:]]
    rh = [max(p.height for p in r) for r in rows]
    title = "Controller-01B: one post-watchdog continuation look for object 210 wall.008"
    sub = [f"look 25: target-valid {m['target_valid_points']:,} | new surfels {m['new_surfels']:,} | active map "
           f"{m['active_map_before']:,} -> {m['active_map_after']:,} | effective {m['effective_before']:,} -> {m['effective_after']:,} | "
           f"OPEN {fpre['frontier_open_count']} -> {fpost['frontier_open_count']} | candidates {fpre['candidates']} -> {fpost['candidates']}",
           f"post-look probe: {post['state']}" + (f", {post['source']} next gaze [{nxt[0]:.1f}, {nxt[1]:.1f}] (not executed)" if nxt else "")
           + f"   ({record['marker']})",
           "Controller-time data and derived renderings only; no evaluation truth. No stopping-policy conclusion is drawn."]
    img = Image.new("RGB", (2 * cw + 42, 40 + 21 * len(sub) + sum(rh) + 42), SURFACE)
    d = ImageDraw.Draw(img); d.text((14, 10), title, fill=INK, font=font(21))
    for n, line in enumerate(sub):
        d.text((14, 40 + 21 * n), line, fill=INK2, font=font(14))
    y = 40 + 21 * len(sub) + 14
    for r, h in zip(rows, rh):
        x = 14
        for p in r:
            img.paste(p, (x, y)); x += cw + 14
        y += h + 14
    vis.mkdir(parents=True, exist_ok=True)
    img.save(vis / "overview.png")
    print(f"{PREFIX} wrote {vis / 'overview.png'} sha256={sha(vis / 'overview.png')}")
    print(f"{PREFIX} visual checks {sum(r['ok'] for r in RESULTS)}/{len(RESULTS)}; firewall violations {len(fw.violations)}")
    return 0 if not fw.violations else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=("run", "check", "visual"))
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--audit", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--visuals", type=Path, default=None)
    a = ap.parse_args()
    if a.mode == "run":
        return cmd_run(a)
    if a.mode == "check":
        return cmd_check(a)
    if a.visuals is None:
        ap.error("--visuals is required for visual mode")
    return cmd_visual(a)


if __name__ == "__main__":
    raise SystemExit(main())
