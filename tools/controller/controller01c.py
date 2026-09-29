#!/usr/bin/env python3
"""Controller-01C: frontier / action correspondence audit of Controller-01B's look 25 (read-only).

    .venv/bin/python tools/controller/controller01c.py audit  --source S --audit A --c01b B --out O
    .venv/bin/python tools/controller/controller01c.py visual --source S --audit A --c01b B --out O --visuals V
    .venv/bin/python tools/controller/controller01c.py check  --source S --audit A --c01b B --out O --visuals V

Contract: docs/controller/controller-01c-frontier-action-correspondence-contract.md.

``audit`` rebuilds the accepted pre-action state with the accepted Controller-01B reconstruction,
reproduces the selected FSG6f candidate and its exact OPEN support, replays look 25 from 01B's saved
acquisition (no render, in a temporary directory) and traces every support element through that look.
``visual`` writes the Level-A figure and a sidecar of its annotated numbers; ``check`` recomputes the
audit and compares it with the saved outputs.  Every mode runs under the truth firewall and writes
nothing into an accepted artifact.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
import tempfile
import time

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[2]
for _p in (REPO, REPO / "tools" / "controller"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import cv2
import numpy as np
from PIL import Image, ImageDraw

import controller01b as B  # the accepted Controller-01B reconstruction, replay and drawing helpers
from fov3d.control import frontier, integrated as ic, object_policy
from fov3d.experiments.classroom_oracle import controller01 as c01
from fov3d.geometry import core as geom
from fov3d.stereo import core as stereo

FR = frontier._legacy_impl  # sealed FSG6f frontier module, read-only (private helpers included)
SF = FR.public.SURFACE_FRONTIER  # the constants the sealed FSG6f code actually reads
RADIUS = float(FR.public.FUSION["association_radius_m"])  # frozen 12 mm association / map-resolution radius
OBJ, GLOBAL_INDEX, LOCAL_STEP = B.OBJ, B.GLOBAL_INDEX, B.LOCAL_STEP
SCHEMA = "Controller01C-audit-v1"
MARKER = "CONTROLLER01C_FRONTIER_ACTION_CORRESPONDENCE_AUDIT_COMPLETE"
C01B_MARKER = "CONTROLLER01B_ONE_LOOK_REPROBE_ACTIONABLE"
EXPECTED = {"own_looks": 24, "pre_gaze": [2.6, 18.2], "selected_gaze": [7.6, 18.2], "effective_pre": 1938913,
            "counts_pre": [350, 52, 28, 270], "candidates": 1, "support": [30, 43, 3, 10], "target_valid": 26950,
            "new_surfels": 0, "counts_same_window_post": [350, 52, 28, 270], "counts_new_window_open": 0,
            "post_state": "ACTIONABLE", "post_source": "cyclopean_epistemic", "post_gaze": [-17.6, 18.9]}
STATE_KEYS = ("frontier_raw_count", "frontier_open_count", "frontier_map_resolved_count", "frontier_boundary_resolved_count")
STATES = ("OPEN", "MAP_RESOLVED", "BOUNDARY_RESOLVED", "NO_LONGER_FRONTIER")
PREFIX = "[controller01c]"
Gate = B.Gate
RESULTS: list[dict] = []


def gate(name: str, ok: bool, detail: str = "", *, hard: bool = True) -> bool:
    RESULTS.append({"check": name, "ok": bool(ok), "detail": detail})
    print(f"{PREFIX} {'PASS' if ok else 'FAIL'} {name}{'' if ok or not detail else ': ' + detail}")
    if not ok and hard:
        raise Gate(f"{name}: {detail}")
    return bool(ok)


def close(a, b, tol=1e-9) -> bool:
    return len(a) == len(b) and all(abs(float(x) - float(y)) <= tol for x, y in zip(a, b))


def js(x):
    return c01._jsonable(x)


# ---------------------------------------------------------------- geometry helpers

def state_of(st: dict, j: int) -> str:
    return "MAP_RESOLVED" if st["map_resolved"][j] else "BOUNDARY_RESOLVED" if st["boundary_resolved"][j] else "OPEN"


def counts_of(st: dict) -> list[int]:
    return [st["raw_count"], st["open_count"], st["map_resolved_count"], st["boundary_resolved_count"]]


def assoc_count(points: np.ndarray, p: np.ndarray, radius: float = RADIUS) -> tuple[int, float]:
    """Look-25 measurements strictly within the association radius of one point, and the nearest distance."""
    if not len(points):
        return 0, math.inf
    d = np.linalg.norm(np.asarray(points, float) - np.asarray(p, float), axis=1)
    return int((d < radius).sum()), float(d.min())


def nearest(points: np.ndarray, p: np.ndarray, chunk: int = 1 << 20) -> float:
    best = math.inf
    for s in range(0, len(points), chunk):
        best = min(best, float(np.linalg.norm(points[s:s + chunk] - p, axis=1).min()))
    return best


def fusion_assignment(map_xyz: np.ndarray, map_ids: np.ndarray, pts: np.ndarray, wanted: int,
                      radius: float, cell: float) -> np.ndarray:
    """The nearest-surfel association of the accepted 12 mm fusion (same hash, offsets, strict order)."""
    key = lambda x: tuple(np.floor(np.asarray(x) / cell).astype(np.int64).tolist())  # noqa: E731
    bins: dict[tuple[int, int, int], list[int]] = {}
    for i, x in enumerate(map_xyz):
        bins.setdefault(key(x), []).append(i)
    offsets = [(a, b, c) for a in (-1, 0, 1) for b in (-1, 0, 1) for c in (-1, 0, 1)]
    out = np.full(len(pts), -1, np.int64)
    for j, x in enumerate(pts):
        k = key(x)
        cand = [i for o in offsets for i in bins.get((k[0] + o[0], k[1] + o[1], k[2] + o[2]), ()) if map_ids[i] == wanted]
        if not cand:
            continue
        cand = np.asarray(cand, np.int64)
        d = np.linalg.norm(map_xyz[cand] - x, axis=1)
        m = int(np.argmin(d))  # first minimum in the fusion's iteration order (strict <)
        if d[m] < radius:
            out[j] = cand[m]
    return out


def trace_point(p: np.ndarray, cal: dict, st: dict, patch: dict, evidence: np.ndarray, full: dict) -> dict:
    """Where one 3-D point falls in look 25, and what look 25 measured there (accepted geometry only).

    ``full`` holds look 25's full rectified instance rasters and the core crop offset: the labels the
    matcher rectifies before cropping its 256 px core (controller-time oracle segmentation)."""
    out: dict = {}
    for side, idk, supk, e in (("L", "ids_left", "raw_support_L", 0), ("R", "ids_right", "raw_support_R", 1)):
        ids = object_policy.relabel_instances(st[idk], OBJ)
        sup = np.asarray(st[supk], bool)
        uv, z = FR._project_rectified_core(cal, p[None], side)
        pe = FR._target_patch_eye_evidence(ids, sup, FR.public.OBJECT_ID, uv, z)
        h, w = ids.shape
        q, zz = uv[0], float(z[0])
        cx, cy = (int(round(q[0])), int(round(q[1]))) if np.isfinite(q).all() else (-1, -1)
        inside = bool(np.isfinite(q).all() and np.isfinite(zz) and zz > 1e-6 and 0 <= cx < w and 0 <= cy < h)
        uvr, zc = geom.project_h(cal["eyes"][e], p[None])
        W, H = cal["image_size_wh"]
        raw_inside = bool(np.isfinite(uvr).all() and zc[0] > 0 and 0 <= uvr[0, 0] <= W - 1 and 0 <= uvr[0, 1] <= H - 1)
        fu, fv = (int(round(q[0])) + full["crop"][0], int(round(q[1])) + full["crop"][1]) if np.isfinite(q).all() else (-1, -1)
        fids = full[side]; fh, fw = fids.shape
        f_in = bool(zz > 1e-6 and 0 <= fu < fw and 0 <= fv < fh)
        rr = max(1, max(2, int(round(min(h, w) * SF["edge_band_fraction"]))) // 2)
        fwin = fids[max(0, fv - rr):fv + rr + 1, max(0, fu - rr):fu + rr + 1] if f_in else np.zeros((0, 0), np.int32)
        out[side] = {"core_uv": [float(q[0]), float(q[1])], "core_depth_m": zz, "inside_core": inside,
                     "inside_full_rectified": f_in, "full_rectified_label": int(fids[fv, fu]) if f_in else None,
                     "full_rectified_patch_210_fraction": float((fwin == OBJ).mean()) if fwin.size else None,
                     "raw_tangent_uv": [float(uvr[0, 0]), float(uvr[0, 1])], "inside_raw_tangent": raw_inside, "observable": bool(pe["observable"][0]),
                     "object_fraction": float(pe["fraction"][0]), "object_pixels": int(pe["object_pixels"][0]),
                     "support_pixels": int(pe["support_pixels"][0]), "patch_radius_px": int(pe["patch_radius_px"])}
    L = out["L"]
    out["full_rectified_label_210_both"] = bool(L["full_rectified_label"] == OBJ and out["R"]["full_rectified_label"] == OBJ)
    out["binocular_observable"] = bool(L["observable"] and out["R"]["observable"])
    out["binocular_object_fraction"] = max(L["object_fraction"], out["R"]["object_fraction"])
    ev = np.asarray(patch["valid"], bool) & (np.asarray(patch["instance_id"]) == OBJ)
    valid_any = np.asarray(patch["valid"], bool)
    n210 = nany = 0
    at_pixel = None
    if L["inside_core"]:
        cx, cy = int(round(L["core_uv"][0])), int(round(L["core_uv"][1])); r = L["patch_radius_px"]
        win = np.s_[max(0, cy - r):cy + r + 1, max(0, cx - r):cx + r + 1]
        n210, nany = int(ev[win].sum()), int(valid_any[win].sum())
        if ev[cy, cx]:
            m = np.asarray(patch["xyz_h"][cy, cx], float)
            eye = np.asarray(cal["eyes"][0]["centre_h_m"], float)
            at_pixel = {"distance_m": float(np.linalg.norm(m - p)),
                        "range_minus_point_range_m": float(np.linalg.norm(m - eye) - np.linalg.norm(p - eye))}
    out["left_patch_valid_210_pixels"] = n210
    out["left_patch_valid_any_pixels"] = nany
    out["measured_210_point_at_pixel"] = at_pixel
    n, dmin = assoc_count(evidence, p)
    out["assoc_12mm_count"] = n
    out["nearest_look25_measurement_m"] = dmin
    return out


def history_tests(p: np.ndarray, history: list[dict]) -> dict:
    """The BOUNDARY_RESOLVED test of every own look for one look-ahead target."""
    tested, fracs = 0, []
    for obs in history:
        per = []
        for side in ("L", "R"):
            uv, z = FR._project_rectified_core(obs["calibration"], p[None], side)
            per.append(FR._target_patch_eye_evidence(obs[f"instance_{side}"], obs[f"raw_support_{side}"],
                                                     FR.public.OBJECT_ID, uv, z))
        if per[0]["observable"][0] and per[1]["observable"][0]:
            tested += 1
            fracs.append(max(float(per[0]["fraction"][0]), float(per[1]["fraction"][0])))
    return {"looks": len(history), "binocular_tests": tested,
            "min_binocular_object_fraction": None if not fracs else min(fracs),
            "tests_below_threshold": int(sum(f < float(SF["edge_object_fraction_min"]) for f in fracs))}


def open_condition(t: np.ndarray, look: dict) -> str:
    L, R = look["L"], look["R"]
    if not (L["inside_core"] and R["inside_core"]):
        return "look-ahead target outside a look-25 core"
    if not look["binocular_observable"]:
        return "look-ahead target in an unsupported look-25 patch"
    if look["binocular_object_fraction"] >= float(SF["edge_object_fraction_min"]):
        return "look-ahead target binocularly observed with 210 present (fraction >= 0.15), no point within 12 mm"
    return "binocular object fraction < 0.15 (would be BOUNDARY_RESOLVED)"


# ---------------------------------------------------------------- the audit

def compute(source: Path, audit_path: Path, c01b: Path, work: Path) -> tuple[dict, dict]:
    """The audit result (JSON-able) and the arrays the visual needs.  Raises Gate on a reproduction failure."""
    for name, digest in B.ACCEPTED.items():
        gate(f"source {name} is the accepted Controller-01 artifact", B.sha(source / name) == digest)
    a01 = json.loads(audit_path.read_text())
    gate("source audit is the accepted Controller-01A result",
         a01.get("outcome") == "FINAL_REPROBE_ACTIONABLE" and a01.get("failure") is None)
    rec01b = json.loads((c01b / "continuation.json").read_text())
    gate("source 01B run is the accepted Controller-01B result (marker, source hashes, one OBSERVE)",
         rec01b.get("marker") == C01B_MARKER and rec01b.get("source_hashes") == B.ACCEPTED
         and rec01b.get("observations_executed") == 1)

    # ---- the accepted pre-action state (01B reconstruction; reproduces the 01A terminal probe)
    run, _actions = B.reconstruct(source, work)
    pre_res, pre = B.validate_pre(run, source, a01)
    ctx = run.ctx[OBJ]
    pre_gaze, pre_cal, st24, hist_pre = tuple(ctx.gaze), ctx.calibration, ctx.state, list(ctx.history)
    geo_pre = np.asarray(run.geometry(OBJ), float)
    sm = ctx.surface_map
    map_pre = {"xyz": np.asarray(sm.xyz_h, float).copy(), "ids": np.asarray(sm.instance_id).copy(),
               "support": np.asarray(sm.support_count).copy(), "prov": np.asarray(sm.provenance_mask).copy(),
               "patches": len(sm.patch_ids)}
    n_map = len(map_pre["xyz"])
    n_mem_pre = int(run.measured_points.get(OBJ, 0))
    dec = run.decisions[OBJ]["fsg6f_decision"]
    sel = dec["selected"]
    sel01a = a01["terminal_probe"]["fsg6f_selected"]
    gate("pre: 210 has 24 own looks; current gaze [2.6, 18.2]; effective geometry 1,938,913 = map + memory",
         len(ctx.visited) == EXPECTED["own_looks"] and close(pre_gaze, EXPECTED["pre_gaze"])
         and len(geo_pre) == EXPECTED["effective_pre"] == n_map + n_mem_pre, f"{len(ctx.visited)} {pre_gaze} {len(geo_pre)}")
    gate("pre: FSG6f frontier 350/52/28/270 and 1 candidate",
         [dec[k] for k in STATE_KEYS] == EXPECTED["counts_pre"] and len(dec["candidates"]) == EXPECTED["candidates"])
    gate("pre: the selected candidate [7.6, 18.2], OPEN/raw/map/boundary support 30/43/3/10, equal to 01A",
         close([sel["yaw_deg"], sel["pitch_deg"]], EXPECTED["selected_gaze"])
         and [sel["frontier_support_count"], sel["raw_frontier_support_count"], sel["map_resolved_support_count"],
              sel["boundary_resolved_support_count"]] == EXPECTED["support"]
         and all(sel[k] == sel01a[k] for k in ("yaw_deg", "pitch_deg", "frontier_support_count", "raw_frontier_support_count",
                                               "map_resolved_support_count", "boundary_resolved_support_count")))

    # ---- the exact candidate support (accepted choose_next formulas on the same frontier arrays)
    fr = frontier.extract_frontier(geo_pre, pre_gaze[0], pre_gaze[1], pre_cal)
    st = frontier.classify_frontier_state(fr, geo_pre, hist_pre)
    gate("support: the re-extracted pre frontier equals the in-process FSG6f decision",
         counts_of(st) == [dec[k] for k in STATE_KEYS] and len(fr["strength"]) == dec["frontier_count"])
    step = float(SF["component_step_deg"])
    dx, dy = int(round((sel["yaw_deg"] - pre_gaze[0]) / step)), int(round((sel["pitch_deg"] - pre_gaze[1]) / step))
    u = np.array([dx, dy], float); u /= np.linalg.norm(u)
    delta = np.c_[fr["target_yaw_deg"] - fr["yaw_deg"], fr["target_pitch_deg"] - fr["pitch_deg"]]
    dn = np.linalg.norm(delta, axis=1); good = dn > 1e-12
    align = np.zeros(len(delta)); align[good] = (delta[good] / dn[good, None]) @ u
    raw = align >= float(SF["alignment_cos_min"])
    support = raw & st["open"]
    score = float(np.sum(fr["strength"][support] * align[support]))
    counts = [int(support.sum()), int(raw.sum()), int((raw & st["map_resolved"]).sum()), int((raw & st["boundary_resolved"]).sum())]
    gate("support: direction and counts reproduce the selected candidate (30/43/3/10)",
         [dx * step, dy * step] == [sel["delta_yaw_deg"], sel["delta_pitch_deg"]] and counts == EXPECTED["support"],
         f"direction ({dx},{dy}) counts {counts}")
    gate("support: frontier score over the 30 elements equals the decision's (identity)",
         abs(score - sel["frontier_score"]) <= 1e-12 * max(1.0, abs(sel["frontier_score"])), f"{score} vs {sel['frontier_score']}")
    proj = FR._project_frontier_pairs(pre_cal, fr["xyz_h"], fr["target_xyz_h"])
    cont = FR._candidate_continuation_from_projected(
        dx, dy, object_policy.relabel_instances(st24["ids_left"], OBJ), st24["raw_support_L"],
        object_policy.relabel_instances(st24["ids_right"], OBJ), st24["raw_support_R"], proj, support, FR.public.OBJECT_ID)
    gate("support: the candidate's continuation evidence recomputed from the support mask equals the decision's (identity)",
         js(cont) == js(sel["continuation"]), f"{cont['per_eye']} vs {sel['continuation']['per_eye']}")

    cell = float(SF["voxel_m"])
    keys = np.floor(fr["xyz_h"] / cell).astype(np.int64)
    fin = np.isfinite(geo_pre).all(1) & (geo_pre[:, 2] < -1e-6)
    gkeys = np.full((len(geo_pre), 3), np.iinfo(np.int64).min, np.int64)
    gkeys[fin] = np.floor(geo_pre[fin] / cell).astype(np.int64)
    raw_idx = np.flatnonzero(raw)
    elements: list[dict] = []
    voxel_surfels: dict[int, np.ndarray] = {}
    for j in raw_idx:
        mem = np.flatnonzero(np.all(gkeys == keys[j], axis=1))
        centroid_ok = bool(len(mem) and np.allclose(geo_pre[mem].mean(axis=0), fr["xyz_h"][j], rtol=0, atol=1e-9))
        surf = mem[mem < n_map]
        voxel_surfels[int(j)] = surf
        yaw_t, pit_t = float(fr["target_yaw_deg"][j]), float(fr["target_pitch_deg"][j])
        elements.append({
            "frontier_index": int(j), "voxel_key_25mm": keys[j].tolist(), "open_support": bool(support[j]),
            "pre_state": state_of(st, j), "x_e": fr["xyz_h"][j].tolist(), "t_e": fr["target_xyz_h"][j].tolist(),
            "x_yaw_pitch_deg": [float(fr["yaw_deg"][j]), float(fr["pitch_deg"][j])], "t_yaw_pitch_deg": [yaw_t, pit_t],
            "strength": float(fr["strength"][j]), "alignment": float(align[j]),
            "voxel": {"effective_points": int(len(mem)), "active_map_surfels": int(len(surf)),
                      "memory_points": int(len(mem) - len(surf)), "active_map_surfel_indices": surf.tolist(),
                      "centroid_reproduced": centroid_ok}})
    gate("support: every element's 25 mm voxel of the effective geometry reproduces its centroid x_e",
         all(e["voxel"]["centroid_reproduced"] for e in elements))

    # ---- replay look 25 (no render; temporary directory), validated against the saved 01B artifacts
    with B.replay_renderer(c01b):
        outcome = run.observe(GLOBAL_INDEX, pre_res.action, LOCAL_STEP)
    post = B.probe_record(run, run.probe(OBJ))
    gate("look 25: replayed post-look probe equals 01B's recorded one (ACTIONABLE, Cyclopean [-17.6, 18.9])",
         post == rec01b["post_probe"] and post["state"] == EXPECTED["post_state"] and post["source"] == EXPECTED["post_source"]
         and close(post["proposed_gaze_deg"], EXPECTED["post_gaze"]))
    gate("look 25: target-valid 26,950 and new surfels 0 (equal to 01B's record)",
         outcome.record["target_valid_points"] == EXPECTED["target_valid"] == rec01b["measurements"]["target_valid_points"]
         and outcome.record["new_surfels"] == EXPECTED["new_surfels"] == rec01b["measurements"]["new_surfels"])
    cal25, st25, hist_post = ctx.calibration, ctx.state, list(ctx.history)
    adir = c01b / f"objects/instance_{OBJ:04d}/acquisitions/fix_{LOCAL_STEP:02d}"
    cal_saved = json.loads((adir / "calibration.json").read_text())
    gate("look 25: the replayed acquisition is 01B's fix_24 (calibration gaze [7.6, 18.2]); 25 own looks",
         cal25 == cal_saved and close(cal25["gaze_yaw_pitch_deg"], EXPECTED["selected_gaze"]) and len(hist_post) == 25)
    sm2 = ctx.surface_map
    saved_map = B.npz(c01b / f"objects/instance_{OBJ:04d}/maps/fix_{LOCAL_STEP:02d}.npz")
    map_post = {"xyz": np.asarray(sm2.xyz_h, float), "support": np.asarray(sm2.support_count),
                "prov": np.asarray(sm2.provenance_mask)}
    gate("look 25: replayed post-look active map equals 01B's saved maps/fix_24.npz",
         np.array_equal(map_post["xyz"].astype(np.float32), saved_map["xyz_h"])
         and np.array_equal(map_post["support"], saved_map["support_count"])
         and np.array_equal(map_post["prov"], saved_map["provenance_mask"]))
    geo_post = np.asarray(run.geometry(OBJ), float)
    patch_path = c01b / f"objects/instance_{OBJ:04d}/patches/fix_{LOCAL_STEP:02d}.npz"
    patch = B.npz(patch_path)
    ev_mask = np.asarray(patch["valid"], bool) & (np.asarray(patch["instance_id"]) == OBJ)
    evidence = np.asarray(patch["xyz_h"], float)[ev_mask]
    snap = run.memory.snapshot(OBJ)
    look_mem = np.asarray(snap.xyz_h[n_mem_pre:], np.float32)
    gate("evidence: exactly the 26,950 instance-210 valid points of look 25 (= its memory additions to 210, source 141)",
         len(evidence) == EXPECTED["target_valid"] and np.array_equal(evidence.astype(np.float32), look_mem)
         and bool(np.all(np.asarray(snap.source_global_index[n_mem_pre:]) == GLOBAL_INDEX)))

    # ---- known answers for the trace calibration (check 7)
    cal_trace, st_trace = cal25, st25
    r25 = stereo.rectification(cal_trace)
    obs25 = B.npz(adir / "oracle_observation.npz")
    full = {"crop": [int(v) for v in r25["crop_xywh"][:2]]}
    for side in ("L", "R"):
        full[side] = stereo.remap(np.asarray(obs25[f"instance_{side}"], np.float32), r25, side, cv2.INTER_NEAREST).astype(np.int32)
    x_, y_, cw_, ch_ = (int(v) for v in r25["crop_xywh"])
    gate("look 25: the full rectified labels cropped to the core equal the matcher's core labels (L and R)",
         np.array_equal(full["L"][y_:y_ + ch_, x_:x_ + cw_], st_trace["ids_left"])
         and np.array_equal(full["R"][y_:y_ + ch_, x_:x_ + cw_], st_trace["ids_right"]))
    vv, uu = np.nonzero(ev_mask)
    uvL, _ = FR._project_rectified_core(cal_trace, evidence, "L")
    uvR, _ = FR._project_rectified_core(cal_trace, evidence, "R")
    errL = np.linalg.norm(uvL - np.c_[uu, vv], axis=1)
    known = {"left_reprojection_error_px": {"median": float(np.median(errL)), "max": float(errL.max())},
             "right_row_difference_px": {"median": float(np.median(np.abs(uvR[:, 1] - vv))), "max": float(np.abs(uvR[:, 1] - vv).max())},
             "disparity_px_min": float((uvL[:, 0] - uvR[:, 0]).min())}
    probe = np.array([0.0, 0.0, -2.0])
    synth = np.array([[0.0119, 0.0, -2.0], [0.0121, 0.0, -2.0]])
    known["synthetic_12mm_association"] = {"count_at_11.9_and_12.1_mm": assoc_count(synth, probe)[0], "radius_m": RADIUS}

    # ---- per-element trace through look 25
    bit = np.uint64(1 << map_pre["patches"])  # fix_24 is the 25th fused patch id of 210's map
    touched = (map_post["prov"] & bit) != 0
    fuse_radius, fuse_cell = float(c01.public.FUSION["association_radius_m"]), float(c01.public.FUSION["hash_cell_m"])
    assign = fusion_assignment(map_pre["xyz"], map_pre["ids"], evidence, OBJ, fuse_radius, fuse_cell)
    sup_delta = map_post["support"].astype(np.int64) - map_pre["support"].astype(np.int64)
    gate("fusion: the re-derived 12 mm assignment touches exactly the surfels whose fix_24 provenance bit was set",
         not bool(np.any(map_pre["prov"] & bit)) and set(np.unique(assign[assign >= 0]).tolist()) == set(np.flatnonzero(touched).tolist())
         and bool(np.all(sup_delta[touched] == 1)) and bool(np.all(sup_delta[~touched] == 0)) and int((assign < 0).sum()) == 0)
    x_all, t_all = fr["xyz_h"][raw_idx], fr["target_xyz_h"][raw_idx]
    mapped_x = FR._target_mapped_mask(x_all, evidence)
    mapped_t = FR._target_mapped_mask(t_all, evidence)
    for n, e in enumerate(elements):
        j = e["frontier_index"]
        e["look25_x"] = trace_point(fr["xyz_h"][j], cal_trace, st_trace, patch, evidence, full)
        e["look25_t"] = trace_point(fr["target_xyz_h"][j], cal_trace, st_trace, patch, evidence, full)
        e["accepted_mask_agrees"] = bool((e["look25_x"]["assoc_12mm_count"] > 0) == bool(mapped_x[n])
                                         and (e["look25_t"]["assoc_12mm_count"] > 0) == bool(mapped_t[n]))
        surf = voxel_surfels[j]
        e["fusion"] = {"voxel_surfels": int(len(surf)), "voxel_surfels_updated": int(touched[surf].sum()),
                       "look25_measurements_fused_into_voxel": int(np.isin(assign, surf).sum()),
                       "support_count_increments": int(sup_delta[surf].sum())}
    gate("association: the 12 mm counts agree with the accepted _target_mapped_mask for every element",
         all(e["accepted_mask_agrees"] for e in elements))

    # ---- same-window post classification (the ORIGINAL pre-look window) and the fixed obligations
    sw_gaze = pre_gaze
    fr_sw = frontier.extract_frontier(geo_post, sw_gaze[0], sw_gaze[1], pre_cal)
    st_sw = frontier.classify_frontier_state(fr_sw, geo_post, hist_post)
    gate("same window: the post-look frontier in the pre-look window is 350/52/28/270 (accepted 01B attribution)",
         counts_of(st_sw) == EXPECTED["counts_same_window_post"], str(counts_of(st_sw)))
    fr_new = frontier.extract_frontier(geo_post, cal25["gaze_yaw_pitch_deg"][0], cal25["gaze_yaw_pitch_deg"][1], cal25)
    st_new = frontier.classify_frontier_state(fr_new, geo_post, hist_post)
    gate("new window: the post-look frontier around the executed gaze has OPEN 0 (01B post probe)",
         counts_of(st_new) == [post["summary"]["fsg6f"][k] for k in STATE_KEYS] and st_new["open_count"] == EXPECTED["counts_new_window_open"])
    keys_sw = {tuple(k): i for i, k in enumerate(np.floor(fr_sw["xyz_h"] / cell).astype(np.int64).tolist())}
    fixed = FR.classify_frontier_state({"target_xyz_h": t_all}, geo_post, hist_post)
    for n, e in enumerate(elements):
        k = keys_sw.get(tuple(e["voxel_key_25mm"]))
        if k is None:
            e["same_window_post"] = {"state": "NO_LONGER_FRONTIER"}
        else:
            e["same_window_post"] = {"state": state_of(st_sw, k), "frontier_index": int(k),
                                     "x_shift_m": float(np.linalg.norm(fr_sw["xyz_h"][k] - fr["xyz_h"][e["frontier_index"]])),
                                     "t_shift_m": float(np.linalg.norm(fr_sw["target_xyz_h"][k] - fr["target_xyz_h"][e["frontier_index"]]))}
        e["fixed_obligation_post_state"] = state_of(fixed, n)
        if e["same_window_post"]["state"] == "OPEN":
            t2 = fr_sw["target_xyz_h"][k]
            look = trace_point(t2, cal_trace, st_trace, patch, evidence, full)
            e["kept_open"] = {"nearest_post_effective_geometry_to_target_m": nearest(geo_post, t2),
                              "look25_condition": open_condition(t2, look),
                              "look25_binocular_object_fraction": look["binocular_object_fraction"],
                              "own_look_history": history_tests(t2, hist_post)}

    # ---- predicted_new_angular_area_deg2: what the accepted code computes for this candidate
    names = run.names
    half = float(pre_cal["nominal_core_fov_deg"]) / 2.0
    q = float(SF["map_extent_quantile"])

    def extent(g):
        y, p_ = FR.angular_coordinates(g)
        return [float(np.quantile(y, q)), float(np.quantile(y, 1 - q))], [float(np.quantile(p_, q)), float(np.quantile(p_, 1 - q))]
    ye, pe = extent(geo_pre)
    area = FR._new_box_area((sel["yaw_deg"], sel["pitch_deg"]), half, tuple(ye), tuple(pe))
    gate("area: _new_box_area on the reconstructed inputs equals the decision's predicted_new_angular_area_deg2",
         abs(area - sel["predicted_new_angular_area_deg2"]) <= 1e-9 and close(ye, dec["map_yaw_extent_deg"], 1e-12)
         and close(pe, dec["map_pitch_extent_deg"], 1e-12))
    box = [sel["yaw_deg"] - half, sel["yaw_deg"] + half, sel["pitch_deg"] - half, sel["pitch_deg"] + half]
    ye2, pe2 = extent(geo_post)
    ey, ep = B.angles(evidence)
    in_box = (ey >= box[0]) & (ey <= box[1]) & (ep >= box[2]) & (ep <= box[3])
    outside_ext = (ey < ye[0]) | (ey > ye[1]) | (ep < pe[0]) | (ep > pe[1])
    allv = np.asarray(patch["valid"], bool) & (np.asarray(patch["instance_id"]) > 0)
    ay, ap = B.angles(np.asarray(patch["xyz_h"], float)[allv])
    a_ids = np.asarray(patch["instance_id"])[allv]
    a_new = ((ay >= box[0]) & (ay <= box[1]) & (ap >= box[2]) & (ap <= box[3])
             & ((ay < ye[0]) | (ay > ye[1]) | (ap < pe[0]) | (ap > pe[1])))
    predicted = {
        "value_deg2": area, "formula": "(2*half)^2 - |candidate box ∩ map extent box|",
        "half_deg": half, "candidate_box_yaw_pitch_deg": box, "map_extent_quantile": q,
        "map_extent_yaw_deg_pre": ye, "map_extent_pitch_deg_pre": pe,
        "intersection_deg2": float((2 * half) ** 2 - area),
        "map_extent_yaw_deg_post": ye2, "map_extent_pitch_deg_post": pe2,
        "same_box_value_post_deg2": FR._new_box_area((sel["yaw_deg"], sel["pitch_deg"]), half, tuple(ye2), tuple(pe2)),
        "look25_target_valid_in_candidate_box": int(in_box.sum()),
        "look25_target_valid_outside_pre_extent": int(outside_ext.sum()),
        "look25_valid_points_in_predicted_new_region_by_instance": {str(int(i)): int((a_ids[a_new] == i).sum()) for i in np.unique(a_ids[a_new])},
        "role": "first candidate sort key (descending), before frontier_score; this decision had one candidate",
        "instance_names": {str(int(i)): names.get(int(i), str(int(i))) for i in np.unique(a_ids[a_new])},
    }

    # ---- summary
    summary = summarize(elements)
    result = {
        "schema": SCHEMA, "contract": "docs/controller/controller-01c-frontier-action-correspondence-contract.md",
        "sources": {"run": str(source), "run_hashes": {n: B.sha(source / n) for n in B.ACCEPTED},
                    "audit_01a": str(audit_path), "run_01b": str(c01b), "01b_marker": rec01b["marker"]},
        "pre": {"own_looks": len(hist_pre), "gaze_deg": list(pre_gaze), "effective_points": len(geo_pre),
                "active_map_surfels": n_map, "frontier_counts": counts_of(st), "candidates": len(dec["candidates"]),
                "consensus_rejected": dec["consensus_rejected_candidate_count"]},
        "candidate": {"gaze_deg": [sel["yaw_deg"], sel["pitch_deg"]], "direction": [dx, dy],
                      "support_counts_open_raw_map_boundary": counts, "frontier_score": score,
                      "continuation_per_eye": js(cont["per_eye"]),
                      "predicted_new_angular_area_deg2": sel["predicted_new_angular_area_deg2"]},
        "look25": {"acquisition": str(adir.relative_to(c01b)), "calibration_gaze_deg": cal25["gaze_yaw_pitch_deg"],
                   "patch_sha256": B.sha(patch_path), "calibration_sha256": B.sha(adir / "calibration.json"),
                   "target_valid_points": int(len(evidence)), "new_surfels": outcome.record["new_surfels"],
                   "effective_points_after": len(geo_post), "surfels_updated_by_fusion": int(touched.sum()),
                   "post_state": post["state"], "post_source": post["source"], "post_gaze_deg": post["proposed_gaze_deg"]},
        "known_answers": known,
        "association_radius_m": RADIUS,
        "same_window": {"gaze_deg": list(sw_gaze), "counts": counts_of(st_sw)},
        "new_window": {"gaze_deg": list(cal25["gaze_yaw_pitch_deg"]), "counts": counts_of(st_new)},
        "elements": elements,
        "predicted_new_angular_area": predicted,
        "summary": summary,
    }
    arrays = {"geo_pre": geo_pre, "geo_post": geo_post, "fr": fr, "st": st, "fr_sw": fr_sw, "st_sw": st_sw,
              "evidence": evidence, "patch": patch, "st25": st25, "pre_gaze": pre_gaze}
    return js(result), arrays


def summarize(elements: list[dict]) -> dict:
    """Every reported count, recomputed from the per-element records only."""
    sup = [e for e in elements if e["open_support"]]

    def xt(key):
        c = {"measured+remains_open": 0, "measured+resolved": 0, "not_measured+remains_open": 0, "not_measured+resolved": 0}
        for e in sup:
            m = "measured" if e[key]["assoc_12mm_count"] > 0 else "not_measured"
            r = "remains_open" if e["same_window_post"]["state"] == "OPEN" else "resolved"
            c[f"{m}+{r}"] += 1
        return c

    def n(pred):
        return int(sum(1 for e in sup if pred(e)))
    out = {
        "candidate_open_support": len(sup), "candidate_raw_aligned_support": len(elements),
        "cross_tab_support_point_x": xt("look25_x"), "cross_tab_lookahead_target_t": xt("look25_t"),
        "projection": {w: {"inside_left_core": n(lambda e: e[w]["L"]["inside_core"]),
                           "inside_right_core": n(lambda e: e[w]["R"]["inside_core"]),
                           "inside_both_cores": n(lambda e: e[w]["L"]["inside_core"] and e[w]["R"]["inside_core"]),
                           "inside_left_raw_tangent": n(lambda e: e[w]["L"]["inside_raw_tangent"]),
                           "full_rectified_label_210_both_eyes": n(lambda e: e[w]["full_rectified_label_210_both"]),
                           "inside_right_raw_tangent": n(lambda e: e[w]["R"]["inside_raw_tangent"]),
                           "binocular_observable": n(lambda e: e[w]["binocular_observable"]),
                           "binocular_observable_with_210_fraction_ge_0.15":
                               n(lambda e: e[w]["binocular_observable"] and e[w]["binocular_object_fraction"] >= float(SF["edge_object_fraction_min"])),
                           "valid_210_depth_in_left_patch": n(lambda e: e[w]["left_patch_valid_210_pixels"] > 0),
                           "assoc_12mm_at_least_one": n(lambda e: e[w]["assoc_12mm_count"] > 0),
                           "assoc_12mm_total": int(sum(e[w]["assoc_12mm_count"] for e in sup))}
                       for w in ("look25_x", "look25_t")},
        "fusion": {"elements_with_updated_voxel_surfels": n(lambda e: e["fusion"]["voxel_surfels_updated"] > 0),
                   "voxel_surfels_updated_total": int(sum(e["fusion"]["voxel_surfels_updated"] for e in sup)),
                   "look25_measurements_fused_into_support_voxels": int(sum(e["fusion"]["look25_measurements_fused_into_voxel"] for e in sup))},
        "same_window_post": {s: n(lambda e, s=s: e["same_window_post"]["state"] == s) for s in STATES},
        "fixed_obligation_post": {s: n(lambda e, s=s: e["fixed_obligation_post_state"] == s) for s in STATES[:3]},
        "kept_open_conditions": {},
        "raw_aligned_same_window_post": {s: int(sum(1 for e in elements if e["same_window_post"]["state"] == s)) for s in STATES},
    }
    kept = [e["kept_open"] for e in sup if "kept_open" in e]
    for k in kept:
        out["kept_open_conditions"][k["look25_condition"]] = out["kept_open_conditions"].get(k["look25_condition"], 0) + 1
    dist = sorted(k["nearest_post_effective_geometry_to_target_m"] for k in kept)
    tested = [k["own_look_history"] for k in kept if k["own_look_history"]["binocular_tests"] > 0]
    out["kept_open_history"] = {
        "elements": len(kept),
        "with_binocular_test_in_25_own_looks": len(tested),
        "binocular_tests_total": int(sum(h["binocular_tests"] for h in tested)),
        "tests_below_0.15": int(sum(h["tests_below_threshold"] for h in tested)),
        "min_binocular_object_fraction": None if not tested else min(h["min_binocular_object_fraction"] for h in tested),
        "nearest_geometry_to_target_m": None if not dist else {"min": dist[0], "median": float(np.median(dist)), "max": dist[-1]}}
    near = sorted(e["look25_x"]["nearest_look25_measurement_m"] for e in sup)
    out["nearest_look25_measurement_to_x_m"] = {"min": near[0], "median": float(np.median(near)), "max": near[-1]}
    return out


# ---------------------------------------------------------------- modes

def cmd_audit(a) -> int:
    source, out = a.source.resolve(), a.out.resolve()
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"output must be new or empty: {out}")
    fw = ic.TruthFirewall(source, c01.is_evaluation_truth)
    t0 = time.perf_counter()
    result: dict = {"schema": SCHEMA}
    try:
        with fw, tempfile.TemporaryDirectory() as tmp:
            result, _ = compute(source, a.audit.resolve(), a.c01b.resolve(), Path(tmp))
    except Gate as exc:
        result["failure"] = str(exc)
    result["reconstruction_gates"] = list(B.RESULTS)
    result["gates"] = list(RESULTS)
    result["truth_firewall"] = {"violations": list(fw.violations), "opened_source_files": sorted(fw.opened)}
    ok = "failure" not in result and not fw.violations
    result["marker"] = MARKER if ok else None
    result["seconds"] = round(time.perf_counter() - t0, 1)
    out.mkdir(parents=True, exist_ok=True)
    (out / "audit.json").write_text(json.dumps(js(result), indent=1, sort_keys=True) + "\n")
    if not ok:
        print(f"{PREFIX} STOPPED: {result.get('failure') or fw.violations} (no marker)")
        return 1
    s = result["summary"]
    print(f"{PREFIX} candidate OPEN support {s['candidate_open_support']} (raw aligned {s['candidate_raw_aligned_support']})")
    for w in ("look25_x", "look25_t"):
        print(f"{PREFIX} {w}: {s['projection'][w]}")
    print(f"{PREFIX} cross-tab (support point x_e): {s['cross_tab_support_point_x']}")
    print(f"{PREFIX} cross-tab (look-ahead target t_e): {s['cross_tab_lookahead_target_t']}")
    print(f"{PREFIX} fusion: {s['fusion']}")
    print(f"{PREFIX} same-window post: {s['same_window_post']}; fixed obligations: {s['fixed_obligation_post']}")
    print(f"{PREFIX} kept OPEN by: {s['kept_open_conditions']}")
    print(f"{PREFIX} predicted_new_angular_area: {result['predicted_new_angular_area']}")
    print(f"{PREFIX} firewall violations {len(fw.violations)}; opened {len(fw.opened)} source files; {result['seconds']} s")
    print(f"{PREFIX} RESULT {MARKER}")
    return 0


VOLATILE = ("seconds", "reconstruction_gates", "gates", "truth_firewall", "marker", "failure")


def cmd_check(a) -> int:
    source, out, vis = a.source.resolve(), a.out.resolve(), a.visuals.resolve()
    saved = json.loads((out / "audit.json").read_text())
    side_path = vis / "frontier-action-correspondence.json"
    side = json.loads(side_path.read_text()) if side_path.exists() else None
    fw = ic.TruthFirewall(source, c01.is_evaluation_truth)
    soft = lambda n, ok, d="": gate(n, ok, d, hard=False)  # noqa: E731
    try:
        with fw, tempfile.TemporaryDirectory() as tmp:
            ok_src = all(B.sha(source / n) == d for n, d in B.ACCEPTED.items()) and saved.get("sources", {}).get("run_hashes") == B.ACCEPTED
            soft("1 source run is the accepted Controller-01 run (hashes, recorded and live)", ok_src)
            if not ok_src:
                raise Gate("wrong source run")
            res, _ = compute(source, a.audit.resolve(), a.c01b.resolve(), Path(tmp))
            a01 = json.loads(a.audit.read_text())["terminal_probe"]["fsg6f_selected"]
            c_s, c_r = saved["candidate"], res["candidate"]
            soft("2 pre-action candidate: saved = recomputed = 01A (counts 30/43/3/10, direction, score)",
                 c_s == c_r and c_s["support_counts_open_raw_map_boundary"] == [a01["frontier_support_count"], a01["raw_frontier_support_count"],
                                                                                a01["map_resolved_support_count"], a01["boundary_resolved_support_count"]]
                 and abs(c_s["frontier_score"] - a01["frontier_score"]) <= 1e-5 * max(1.0, abs(a01["frontier_score"])))
            soft("3 selected gaze [7.6, 18.2]: saved = recomputed = 01A = 01B action",
                 close(c_s["gaze_deg"], EXPECTED["selected_gaze"]) and c_s["gaze_deg"] == c_r["gaze_deg"]
                 and c_s["gaze_deg"] == [a01["yaw_deg"], a01["pitch_deg"]]
                 and json.loads((a.c01b / "continuation.json").read_text())["action"]["gaze_deg"] == c_s["gaze_deg"])
            sup_s = [e for e in saved["elements"] if e["open_support"]]
            sup_r = [e for e in res["elements"] if e["open_support"]]
            soft("4 the 30 OPEN support elements (and 43 raw aligned): saved set = recomputed set",
                 len(sup_s) == len(sup_r) == 30 and len(saved["elements"]) == len(res["elements"]) == 43
                 and [e["frontier_index"] for e in sup_s] == [e["frontier_index"] for e in sup_r])
            ident = lambda e: (e["frontier_index"], tuple(e["voxel_key_25mm"]), tuple(e["x_e"]), tuple(e["t_e"]), e["pre_state"])  # noqa: E731
            soft("5 support identity (index, voxel key, x_e, t_e, state) equals the recomputed, element by element",
                 [ident(e) for e in saved["elements"]] == [ident(e) for e in res["elements"]])
            l_s, l_r = saved["look25"], res["look25"]
            soft("6 look-25 acquisition is 01B's fix_24 (path, calibration gaze, patch/calibration hashes, 26,950)",
                 l_s == l_r and l_s["acquisition"] == f"objects/instance_{OBJ:04d}/acquisitions/fix_{LOCAL_STEP:02d}"
                 and close(l_s["calibration_gaze_deg"], EXPECTED["selected_gaze"]) and l_s["target_valid_points"] == EXPECTED["target_valid"])
            k = res["known_answers"]
            soft("7 projection known answer: look 25's own measurements reproject onto their pixels (L) and rows (R)",
                 k["left_reprojection_error_px"]["median"] < 0.5 and k["left_reprojection_error_px"]["max"] < 1.0
                 and k["right_row_difference_px"]["max"] < 1.0 and k["disparity_px_min"] > 0
                 and saved["known_answers"] == k
                 and all(e["look25_x"]["L"]["core_uv"] == f["look25_x"]["L"]["core_uv"] for e, f in zip(saved["elements"], res["elements"])),
                 str(k))
            soft("8 association uses the accepted 12 mm rule (radius, synthetic 11.9/12.1 mm known answer, accepted mask)",
                 saved["association_radius_m"] == res["association_radius_m"] == 0.012
                 and k["synthetic_12mm_association"]["count_at_11.9_and_12.1_mm"] == 1
                 and all(e["accepted_mask_agrees"] for e in res["elements"])
                 and [(e["look25_x"]["assoc_12mm_count"], e["look25_t"]["assoc_12mm_count"]) for e in saved["elements"]]
                 == [(e["look25_x"]["assoc_12mm_count"], e["look25_t"]["assoc_12mm_count"]) for e in res["elements"]])
            patch = B.npz(a.c01b / f"objects/instance_{OBJ:04d}/patches/fix_{LOCAL_STEP:02d}.npz")
            n210 = int((np.asarray(patch["valid"], bool) & (np.asarray(patch["instance_id"]) == OBJ)).sum())
            soft("9 target-210 evidence only: the evidence set is the 26,950 instance-210 valid points",
                 n210 == EXPECTED["target_valid"] == l_r["target_valid_points"] == l_s["target_valid_points"])
            soft("10 same-window classification uses the pre-look window [2.6, 18.2] (350/52/28/270), element states equal",
                 saved["same_window"] == res["same_window"] and close(saved["same_window"]["gaze_deg"], EXPECTED["pre_gaze"])
                 and saved["same_window"]["counts"] == EXPECTED["counts_same_window_post"]
                 and [e["same_window_post"] for e in saved["elements"]] == [e["same_window_post"] for e in res["elements"]])
            soft("11 truth firewall: no violation in the audit record or this check",
                 saved.get("truth_firewall", {}).get("violations") == [] and not fw.violations)
            summ_ok = saved["summary"] == summarize(saved["elements"]) == res["summary"]
            side_ok = side is not None and side.get("summary") == saved["summary"] and side.get("marker") == saved.get("marker") == MARKER
            rest = {k2: v for k2, v in saved.items() if k2 not in VOLATILE} == {k2: v for k2, v in res.items() if k2 not in VOLATILE}
            soft("12 summary and visual counts equal the per-element records and the recomputation", summ_ok and side_ok and rest,
                 f"summary {summ_ok} sidecar {side_ok} full record {rest}")
    except Gate as exc:
        print(f"{PREFIX} CHECK STOPPED: {exc}")
    except Exception as exc:  # noqa: BLE001
        print(f"{PREFIX} CHECK ERROR: {type(exc).__name__}: {exc}")
        RESULTS.append({"check": "check completed without error", "ok": False, "detail": f"{type(exc).__name__}: {exc}"})
    if fw.violations:
        RESULTS.append({"check": "check-mode truth firewall", "ok": False, "detail": str(fw.violations)})
    allr = B.RESULTS + RESULTS
    bad = sum(not r["ok"] for r in allr)
    print(f"{PREFIX} SUMMARY checked={len(allr)} failed={bad}")
    return 1 if bad else 0


GREEN, RED, AMBER, PURPLE, GRAY2 = (27, 150, 72), (200, 40, 40), (222, 160, 20), (130, 70, 180), (150, 148, 142)
STATE_COL = {"OPEN": B.ORANGE, "MAP_RESOLVED": B.BLUE, "BOUNDARY_RESOLVED": B.AQUA, "NO_LONGER_FRONTIER": (60, 60, 60)}


def x_class(e: dict) -> tuple[str, tuple]:
    L = e["look25_x"]
    if L["assoc_12mm_count"] > 0:
        return "measured: >= 1 look-25 point of 210 within 12 mm", GREEN
    if L["L"]["inside_core"] and L["R"]["inside_core"]:
        return "inside both cores, no look-25 point within 12 mm", AMBER
    return "outside a look-25 core", RED


def t_class(e: dict) -> tuple[str, tuple]:
    T = e["look25_t"]
    if T["assoc_12mm_count"] > 0:
        return "look-ahead target measured (point within 12 mm)", GREEN
    if not (T["L"]["inside_core"] and T["R"]["inside_core"]):
        return "look-ahead target outside a look-25 core", RED
    if not T["binocular_observable"]:
        return "look-ahead target in an unsupported patch", GRAY2
    if T["binocular_object_fraction"] >= float(SF["edge_object_fraction_min"]):
        return "look-ahead target seen as 210 (fraction >= 0.15), no point within 12 mm", PURPLE
    return "look-ahead target seen without 210 (fraction < 0.15)", B.AQUA


def draw_elements(img, ch, elements, colour_of, arrows=True, ring=True):
    im = Image.fromarray(img); d = ImageDraw.Draw(im)
    for e in elements:
        x0, y0 = (float(v) for v in ch.px(*e["x_yaw_pitch_deg"]))
        x1, y1 = (float(v) for v in ch.px(*e["t_yaw_pitch_deg"]))
        col = colour_of(e)
        if arrows:
            d.line([x0, y0, x1, y1], fill=col, width=2)
            d.line([x1 - 4, y1 - 4, x1 + 4, y1 + 4], fill=col, width=2); d.line([x1 - 4, y1 + 4, x1 + 4, y1 - 4], fill=col, width=2)
        d.ellipse([x0 - 5, y0 - 5, x0 + 5, y0 + 5], fill=col, outline=B.INK if ring else col, width=1)
    return np.asarray(im)


def box(img, ch, centre, half, col, width=3, label=None, dash=False):
    im = Image.fromarray(img); d = ImageDraw.Draw(im)
    x0, y0 = (float(v) for v in ch.px(centre[0] - half, centre[1] + half))
    x1, y1 = (float(v) for v in ch.px(centre[0] + half, centre[1] - half))
    if dash:
        for a0 in np.arange(0, 1, 0.04):
            a1 = a0 + 0.02
            for (ax, ay, bx, by) in ((x0, y0, x1, y0), (x0, y1, x1, y1), (x0, y0, x0, y1), (x1, y0, x1, y1)):
                d.line([ax + (bx - ax) * a0, ay + (by - ay) * a0, ax + (bx - ax) * a1, ay + (by - ay) * a1], fill=col, width=width)
    else:
        d.rectangle([x0, y0, x1, y1], outline=col, width=width)
    if label:
        f = B.font(13); tw = d.textlength(label, font=f)
        d.rectangle([x0 + 2, y0 + 2, x0 + tw + 8, y0 + 20], fill=(255, 255, 255)); d.text((x0 + 5, y0 + 3), label, fill=col, font=f)
    return np.asarray(im)


def legend_rows(items, width):
    rows, cur, x = [], [], 6
    for col, label in items:
        w = 34 + ImageDraw.Draw(Image.new("RGB", (1, 1))).textlength(label, font=B.font(13))
        if cur and x + w > width:
            rows.append(cur); cur, x = [], 6
        cur.append((col, label)); x += w
    rows.append(cur)
    return B.vstack(*[B.legend(r, width) for r in rows], gap=0)


def ortho_view(elements, geo, evidence, frame, axes, size, extent, slab, title, nearest_pair=None):
    """Orthographic view of the support neighbourhood in a local frame (metres)."""
    c, e1, e2, r = frame
    ax = {"right": e1, "up": e2, "depth": r}
    a, b = ax[axes[0]], ax[axes[1]]
    third = [v for k, v in ax.items() if k not in axes][0]
    w, h = size
    s = min(w / (extent[0][1] - extent[0][0]), h / (extent[1][1] - extent[1][0]))
    w, h = int(round((extent[0][1] - extent[0][0]) * s)), int(round((extent[1][1] - extent[1][0]) * s))
    img = np.full((h, w, 3), B.SURFACE, np.uint8)

    def to_px(p):
        q = np.asarray(p, float).reshape(-1, 3) - c
        return (q @ a - extent[0][0]) * s, h - (q @ b - extent[1][0]) * s

    def splat(p, col):
        p = np.asarray(p, float).reshape(-1, 3)
        p = p[np.abs((p - c) @ third) <= slab]
        x, y = to_px(p)
        keep = (x >= 0) & (x < w) & (y >= 0) & (y < h)
        img[y[keep].astype(int), x[keep].astype(int)] = col
    splat(geo[:: max(1, len(geo) // 2000000)], B.OLD_PTS)
    splat(evidence, B.ORANGE)
    im = Image.fromarray(img); d = ImageDraw.Draw(im)
    if nearest_pair is not None:
        (x0,), (y0,) = to_px(nearest_pair[0]); (x1,), (y1,) = to_px(nearest_pair[1])
        for t0 in np.arange(0, 1, 0.06):
            d.line([x0 + (x1 - x0) * t0, y0 + (y1 - y0) * t0, x0 + (x1 - x0) * (t0 + 0.03), y0 + (y1 - y0) * (t0 + 0.03)], fill=B.INK, width=2)
        lab = f"nearest look-25 measurement: {np.linalg.norm(np.subtract(nearest_pair[1], nearest_pair[0])):.2f} m"
        f = B.font(13); tw = d.textlength(lab, font=f); lx, ly = min(x1 + 10, w - tw - 6), y1 + 8
        d.rectangle([lx - 3, ly - 1, lx + tw + 3, ly + 17], fill=(255, 255, 255)); d.text((lx, ly), lab, fill=B.INK, font=f)
    for e in elements:
        (x0,), (y0,) = to_px(e["x_e"]); (x1,), (y1,) = to_px(e["t_e"])
        d.line([x0, y0, x1, y1], fill=B.INK2, width=1)
        tc = t_class(e)[1]
        d.line([x1 - 4, y1 - 4, x1 + 4, y1 + 4], fill=tc, width=2); d.line([x1 - 4, y1 + 4, x1 + 4, y1 - 4], fill=tc, width=2)
        d.ellipse([x0 - 5, y0 - 5, x0 + 5, y0 + 5], fill=x_class(e)[1], outline=B.INK, width=1)
    bar = 0.10 * s
    d.line([12, h - 14, 12 + bar, h - 14], fill=B.INK, width=3); d.text((16 + bar, h - 22), "0.10 m", fill=B.INK, font=B.font(12))
    d.rectangle([0, 0, d.textlength(title, font=B.font(14)) + 10, 20], fill=(255, 255, 255)); d.text((4, 2), title, fill=B.INK, font=B.font(14))
    return np.asarray(im)


def rectified_full(obs: dict, cal: dict, side: str) -> tuple[np.ndarray, np.ndarray]:
    """Look 25's full rectified raster (the matcher's rectification) and its instance labels."""
    r = stereo.rectification(cal)
    rgb = stereo.remap(np.asarray(obs[f"rgb_{side}"], np.float32), r, side, cv2.INTER_LINEAR)
    ids = stereo.remap(np.asarray(obs[f"instance_{side}"], np.float32), r, side, cv2.INTER_NEAREST).astype(np.int32)
    u8 = np.rint(np.power(np.clip(rgb, 0.0, 1.0), 1.0 / 2.2) * 255.0).astype(np.uint8)  # the benchmark-image encoding
    return u8, ids


def cmd_visual(a) -> int:
    source, out, vis = a.source.resolve(), a.out.resolve(), a.visuals.resolve()
    saved = json.loads((out / "audit.json").read_text())
    fw = ic.TruthFirewall(source, c01.is_evaluation_truth)
    try:
        with fw, tempfile.TemporaryDirectory() as tmp:
            res, arr = compute(source, a.audit.resolve(), a.c01b.resolve(), Path(tmp))
            gate("visual: the recomputed audit equals the saved audit.json (summary and per-element records)",
                 res["summary"] == saved["summary"] == summarize(saved["elements"]) and res["elements"] == saved["elements"])
            adir = a.c01b / f"objects/instance_{OBJ:04d}/acquisitions/fix_{LOCAL_STEP:02d}"
            cal25 = json.loads((adir / "calibration.json").read_text())
            obs = B.npz(adir / "oracle_observation.npz")
            full = {side: rectified_full(obs, cal25, side) for side in ("L", "R")}
    except Gate as exc:
        print(f"{PREFIX} VISUAL REFUSED: {exc}")
        return 1
    s = saved["summary"]; els = saved["elements"]
    sup = [e for e in els if e["open_support"]]
    pre_gaze, sel_gaze = saved["pre"]["gaze_deg"], saved["candidate"]["gaze_deg"]
    half = saved["predicted_new_angular_area"]["half_deg"]
    win = half + float(SF["current_view_margin_deg"])
    ch = B.Chart(pre_gaze[0] - 8.5, sel_gaze[0] + 8.5, pre_gaze[1] - 8.5, pre_gaze[1] + 8.5, 820)
    fr, st, fr_sw, st_sw = arr["fr"], arr["st"], arr["fr_sw"], arr["st_sw"]
    pr, ct, sw, hist = s["projection"], s["cross_tab_support_point_x"], s["same_window_post"], s["kept_open_history"]

    def frontier_layer(geo, frx, stx):
        img = B.render(ch, geo[:: max(1, len(geo) // 500000)], B.OLD_PTS)
        cols = np.zeros((len(frx["xyz_h"]), 3), np.uint8)
        cols[stx["map_resolved"]] = B.BLUE; cols[stx["boundary_resolved"]] = B.AQUA; cols[stx["open"]] = B.ORANGE
        return B.render(ch, frx["xyz_h"], cols, radius=2, img=img)

    # 1. pre-action frontier
    img = frontier_layer(arr["geo_pre"], fr, st)
    img = box(img, ch, pre_gaze, win, GRAY2, width=2, label="FSG6f frontier window around look 24", dash=True)
    img = box(img, ch, sel_gaze, half, B.ORANGE, label="look 25 core [7.6, 18.2]")
    img = box(img, ch, pre_gaze, half, B.INK, label="look 24 core [2.6, 18.2]")
    img = draw_elements(img, ch, sup, lambda e: B.ORANGE)
    c = saved["candidate"]
    xs_yaw = [e["x_yaw_pitch_deg"][0] for e in sup]
    p1 = B.panel(B.vstack(img, legend_rows([(B.ORANGE, "OPEN"), (B.BLUE, "MAP_RESOLVED"), (B.AQUA, "BOUNDARY_RESOLVED"),
                                            (B.INK, "ringed + arrow: the 30 OPEN support elements x_e -> look-ahead target t_e")], ch.w)),
                 "1. PRE-ACTION FRONTIER: the support that requested [7.6, 18.2]", "DERIVED",
                 [f"frontier raw/OPEN/map/boundary {'/'.join(map(str, saved['pre']['frontier_counts']))}; candidate +yaw: OPEN support "
                  f"{c['support_counts_open_raw_map_boundary'][0]} of {c['support_counts_open_raw_map_boundary'][1]} raw aligned",
                  f"the 30 support elements lie at yaw {min(xs_yaw):.1f} to {max(xs_yaw):.1f} deg; their look-ahead targets point to +yaw;",
                  "the candidate gaze is look 24's gaze plus one 5-deg lattice step in that direction (accepted choose_next)",
                  "elements = 25 mm voxel centroids of 210's effective geometry; state = FSG6f class of the look-ahead target"])
    # 2. look-25 binocular observation: the full rectified rasters with the matcher's 256 px core outlined
    k = 0.8
    crop = [int(v) for v in stereo.rectification(cal25)["crop_xywh"]]
    x0, y0, cw_, chh = crop
    patch = arr["patch"]
    ev = np.asarray(patch["valid"], bool) & (np.asarray(patch["instance_id"]) == OBJ)

    def eye_image(side):
        rgb, ids = full[side]
        img2 = rgb.copy()
        if side == "L":
            core = img2[y0:y0 + chh, x0:x0 + cw_]
            core[ev] = (0.35 * core[ev] + 0.65 * np.array(B.ORANGE)).astype(np.uint8)
        img2 = cv2.resize(img2, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
        m = cv2.resize((ids == OBJ).astype(np.uint8), (img2.shape[1], img2.shape[0]), interpolation=cv2.INTER_NEAREST)
        cs, _ = cv2.findContours(m, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
        cv2.drawContours(img2, cs, -1, B.BLUE, 2)
        im = Image.fromarray(img2); d = ImageDraw.Draw(im)
        d.rectangle([k * x0, k * y0, k * (x0 + cw_), k * (y0 + chh)], outline=B.INK, width=3)
        lab = "256 px core: depth is measured here"
        d.rectangle([k * x0 + 2, k * y0 + 2, k * x0 + 8 + d.textlength(lab, font=B.font(12)), k * y0 + 19], fill=B.INK)
        d.text((k * x0 + 5, k * y0 + 4), lab, fill=(255, 255, 255), font=B.font(12))
        for e in sup:
            for key, cls, shape in (("look25_x", x_class, "o"), ("look25_t", t_class, "x")):
                u, v = e[key][side]["core_uv"]
                u, v = k * (u + x0), k * (v + y0)
                col = cls(e)[1]
                if shape == "o":
                    d.ellipse([u - 4, v - 4, u + 4, v + 4], outline=col, width=2)
                else:
                    d.line([u - 4, v - 4, u + 4, v + 4], fill=col, width=2); d.line([u - 4, v + 4, u + 4, v - 4], fill=col, width=2)
        return np.asarray(im)
    p2 = B.panel(B.vstack(B.hstack(B.labelled(eye_image("L"), "left eye, full rectified raster"), B.labelled(eye_image("R"), "right eye")),
                          legend_rows([(B.BLUE, "outline of 210's labels"), (B.ORANGE, "210 matcher-valid depth (left core)"),
                                       (RED, "o x_e / x t_e outside the cores"),
                                       (GREEN, "measured within 12 mm"), (AMBER, "inside both cores, not measured")], 1032)),
                 "2. LOOK-25 BINOCULAR OBSERVATION: where the same 30 elements fall", "CONTROLLER-TIME",
                 [f"x_e inside both cores {pr['look25_x']['inside_both_cores']}/30 (inside both raw tangent images "
                  f"{min(pr['look25_x']['inside_left_raw_tangent'], pr['look25_x']['inside_right_raw_tangent'])}/30); binocular-observable "
                  f"{pr['look25_x']['binocular_observable']}; valid 210 depth in its left patch {pr['look25_x']['valid_210_depth_in_left_patch']}",
                  f"t_e inside both cores {pr['look25_t']['inside_both_cores']}/30; binocular-observable {pr['look25_t']['binocular_observable']}; "
                  f"labelled 210 in both full rasters: x_e {pr['look25_x']['full_rectified_label_210_both_eyes']}/30, "
                  f"t_e {pr['look25_t']['full_rectified_label_210_both_eyes']}/30",
                  "images and labels are controller-time; the projections are DERIVED with look 25's calibration"])
    # 3. 3-D correspondence
    xs = np.array([e["x_e"] for e in sup]); ts = np.array([e["t_e"] for e in sup])
    cen = xs.mean(axis=0); r = cen / np.linalg.norm(cen)
    e1 = np.cross(r, [0.0, 1.0, 0.0]); e1 /= np.linalg.norm(e1); e2 = np.cross(e1, r)
    frame = (cen, e1, e2, r)
    evid = arr["evidence"]
    dmin = np.full(len(xs), np.inf); jmin = np.zeros(len(xs), int)
    for i2, x in enumerate(xs):
        dd = np.linalg.norm(evid - x, axis=1); jmin[i2] = int(np.argmin(dd)); dmin[i2] = dd[jmin[i2]]
    i_best = int(np.argmin(dmin)); pair = (xs[i_best], evid[jmin[i_best]])
    rel = np.vstack([xs, ts, pair[1]]) - cen
    ex1 = (float((rel @ e1).min()) - 0.25, float((rel @ e1).max()) + 0.55)
    ex2 = (float((rel @ e2).min()) - 0.12, float((rel @ e2).max()) + 0.12)
    front = ortho_view(sup, arr["geo_pre"], evid, frame, ("right", "up"), (1032, 470), (ex1, ex2), 0.30,
                       "front view (from the head; slab +-0.30 m in depth)", pair)
    top = ortho_view(sup, arr["geo_pre"], evid, frame, ("right", "depth"), (1032, 230), (ex1, (-0.35, 0.35)), 0.45,
                     "top view (up = farther from the head)", pair)
    nx = s["nearest_look25_measurement_to_x_m"]
    p3 = B.panel(B.vstack(front, top, legend_rows([(B.OLD_PTS, "210 effective geometry before look 25"),
                                                   (B.ORANGE, f"look-25 measurements of 210 ({saved['look25']['target_valid_points']:,})"),
                                                   (RED, "support x_e (dot) / t_e (x): no look-25 point within 12 mm")], 1032)),
                 "3. 3-D CORRESPONDENCE: support elements and look-25 measurements", "CONTROLLER-TIME",
                 [f"x_e with >= 1 look-25 measurement within 12 mm: {pr['look25_x']['assoc_12mm_at_least_one']}/30; t_e: "
                  f"{pr['look25_t']['assoc_12mm_at_least_one']}/30; nearest look-25 measurement to x_e {nx['min']:.2f} to {nx['max']:.2f} m",
                  f"fusion: {s['fusion']['look25_measurements_fused_into_support_voxels']} look-25 points fused into the support voxels' surfels "
                  f"({s['fusion']['voxel_surfels_updated_total']} of their surfels updated)",
                  "points are controller-time; element positions and 12 mm associations are DERIVED"])
    # 4. same-window post classification
    img = frontier_layer(arr["geo_post"], fr_sw, st_sw)
    img = box(img, ch, pre_gaze, win, GRAY2, width=2, label="the SAME pre-look window, after look 25", dash=True)
    img = box(img, ch, sel_gaze, half, B.ORANGE, width=2)
    img = draw_elements(img, ch, sup, lambda e: STATE_COL[e["same_window_post"]["state"]])
    nd = hist["nearest_geometry_to_target_m"]
    p4 = B.panel(B.vstack(img, legend_rows([(STATE_COL[k2], f"{k2} {sw[k2]}") for k2 in STATES], ch.w)),
                 "4. SAME-WINDOW POST CLASSIFICATION: the same elements after look 25", "DERIVED",
                 [f"pre-look window after look 25: {'/'.join(map(str, saved['same_window']['counts']))} (raw/OPEN/map/boundary); "
                  f"new window: {'/'.join(map(str, saved['new_window']['counts']))}",
                  f"measured+OPEN {ct['measured+remains_open']} | measured+resolved {ct['measured+resolved']} | "
                  f"not measured+OPEN {ct['not_measured+remains_open']} | not measured+resolved {ct['not_measured+resolved']}",
                  "kept OPEN in look 25 by: " + "; ".join(f"{v} {k2}" for k2, v in s["kept_open_conditions"].items()),
                  f"earlier own looks: {hist['with_binocular_test_in_25_own_looks']} of these t_e were binocularly tested "
                  f"({hist['binocular_tests_total']} tests, 210 fraction >= {hist['min_binocular_object_fraction']:.2f});"
                  f" t_e to geometry {nd['min'] * 1000:.0f}-{nd['max'] * 1000:.0f} mm (> 12 mm)"])
    panels = [p1, p2, p3, p4]
    cw = max(p.width for p in panels); rows = [panels[:2], panels[2:]]
    rh = [max(p.height for p in rr) for rr in rows]
    title = "Controller-01C: did look 25 service the frontier that asked for it?"
    sub = [f"object 210 wall.008 | FSG6f chose [7.6, 18.2] from 30 OPEN support elements at yaw {min(xs_yaw):.1f}..{max(xs_yaw):.1f} deg | "
           f"look 25: {saved['look25']['target_valid_points']:,} target-valid points, {saved['look25']['new_surfels']} new surfels",
           f"measured: support inside look 25's cores {pr['look25_x']['inside_both_cores']}/30 | measured within 12 mm "
           f"{pr['look25_x']['assoc_12mm_at_least_one']}/30 | same-window post OPEN {sw['OPEN']}, map {sw['MAP_RESOLVED']}, "
           f"boundary {sw['BOUNDARY_RESOLVED']}, retired {sw['NO_LONGER_FRONTIER']}",
           "Controller-time data and derived renderings only; no evaluation truth. No action-targeting or stopping-policy conclusion is drawn."]
    im = Image.new("RGB", (2 * cw + 42, 40 + 21 * len(sub) + sum(rh) + 42), B.SURFACE)
    d = ImageDraw.Draw(im); d.text((14, 10), title, fill=B.INK, font=B.font(21))
    for n, line in enumerate(sub):
        d.text((14, 40 + 21 * n), line, fill=B.INK2, font=B.font(14))
    y = 40 + 21 * len(sub) + 14
    for rr, h in zip(rows, rh):
        x = 14
        for p in rr:
            im.paste(p, (x, y)); x += cw + 14
        y += h + 14
    vis.mkdir(parents=True, exist_ok=True)
    png = vis / "frontier-action-correspondence.png"
    im.save(png)
    (vis / "frontier-action-correspondence.json").write_text(json.dumps(js({
        "truth": "CONTROLLER-TIME images, labels and points; DERIVED projections, associations and classifications; no evaluation truth",
        "marker": saved["marker"], "summary": saved["summary"], "png_sha256": B.sha(png)}), indent=1, sort_keys=True) + "\n")
    print(f"{PREFIX} wrote {png} sha256={B.sha(png)}")
    print(f"{PREFIX} visual checks {sum(r['ok'] for r in B.RESULTS + RESULTS)}/{len(B.RESULTS + RESULTS)}; firewall violations {len(fw.violations)}")
    return 0 if not fw.violations else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=("audit", "check", "visual"))
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--audit", type=Path, required=True)
    ap.add_argument("--c01b", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--visuals", type=Path, default=None)
    a = ap.parse_args()
    if a.mode == "audit":
        return cmd_audit(a)
    if a.visuals is None:
        ap.error("--visuals is required for check and visual modes")
    return cmd_check(a) if a.mode == "check" else cmd_visual(a)


if __name__ == "__main__":
    raise SystemExit(main())
