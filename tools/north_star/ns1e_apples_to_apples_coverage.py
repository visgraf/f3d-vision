"""NS1e apples-to-apples coverage diagnostic (read-only; no render, no Blender, no controller, no stereo).

Question (fast diagnostic, 2026-10-06): does the final NS1e persistent reconstruction cover the SAME historical
Controller-01 reachable surface nearly as well as the old Controller-01 reconstruction?

- PRIMARY (A vs C): for every id common to the Controller-01 localized objects and the ten NS1e scheduler entities,
  both final persistent maps against the identical Controller-01 0.25-degree cyclopean reachable samples of that id,
  with the accepted ``classroom_oracle1_eval._covered`` at 12 mm.
- SECONDARY (B vs D): both maps against the accepted Breadth-1 0.5-degree whole-sphere first-hit reference (the
  reference NS1e's own evaluation used), split by the old Controller domain with the Breadth-1 definition (cell-centre
  yaw in [-25, 25] and pitch in [-20, 20], closed).

Known answers (fail-capable): the Controller-01 map on the historical reference must reproduce the accepted
Controller-01 ``evaluation.json`` counts; the NS1e map on Breadth-1 must reproduce NS1e ``evaluation/coverage.npz``
bitwise.  Frame guard: one canonical fixed-head H frame, from metadata, code provenance and a geometric cross-check
with a wrong-frame negative control.  The whole computation runs twice and must give identical numbers.

Both runs are opened read-only; an audit hook refuses any write outside --out.
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
from pathlib import Path  # noqa: E402
import subprocess  # noqa: E402
import time  # noqa: E402
from typing import Any  # noqa: E402

import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _p in (HERE, HERE.parent / "classroom_oracle", HERE.parent / "visual_language", HERE.parent, REPO):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import breadth1_glance as BG1  # noqa: E402  (accepted Breadth-1 EXR extraction / orientation test, read-only)
import breadth1_spec as B1S  # noqa: E402  (accepted cell weights, yaw/pitch convention, old-domain bounds)
import classroom_oracle1_eval as EV  # noqa: E402  (accepted exact 12-mm coverage and map loader, sealed)
import ns1e_core as CORE  # noqa: E402  (accepted NS1e reference resolver / evaluation helpers, read-only)
import ns1e_spec as SP  # noqa: E402

PREFIX = "[ns1e-a2a]"
SCHEMA = "NS1e-apples-to-apples-coverage-v1"
STATUS = "DIAGNOSTIC — REVIEW PENDING"
RADIUS_M = 0.012

# Accepted Controller-01 full run (docs/controller/controller-01-state-action-report.md, "Full run").
C01_PINS = {
    "manifest.json": "d293a98fd6bb285e882186af8fbeadba29ab1d1d62efea23f3ed0ff5c62c0e91",
    "actions.json": "12cdbe4d760cce6c494075e4368f9424805b51b997b8b21724bf87f71cc55afd",
    "evaluation.json": "76cb1e5df88ea401aed6409327bd51fc149fa05b174a1e67b014e671b34512b6",
}
# Canonical NS1e run (docs/north-star/ns1e-coherent-full-loop-m2-memory-report.md, section 1; full values measured).
NS1E_PINS = {
    "manifest.json": "a707ade2ca817740758251231bb7241529dbb347433ec4bfb6ad0dcc0f027dae",
    "scene/terminal.json": "6f86e9ba77ce904ca0ece704dd928b4d3dbe85ac0aa79725eb049994547a66df",
    "control/control-manifest.json": "bd41663b3a2905396ece5484d79f838c1f3438af35ae77080f06ee9d1ae930f3",
    "freeze/control-freeze.json": "fa07a712111e8b41d9bced4521ce533cda1b4bb736077c8562a8603c960775ab",
    "evaluation/evaluation.json": "e30da7220239a295ade18d24340a4cc790a737be1ed743878e1376bade235393",
}
EVALUATOR_SHA256 = "b9f707e6a3a52fb525a9252a581097ced75a6f9d90f3b850d4b0bb783d04053b"  # ns1e_spec pin
H_FRAME = "H: fixed head; +X right, +Y up, -Z forward; metres"
EYE_CENTRES_H = [[-0.0315, 0.0, 0.0], [0.0315, 0.0, 0.0]]
# Frame cross-check bounds (declared before the first run): the correct transform must put the historical samples on
# the Breadth-1 surface (0.5 deg cells at <= ~5 m are <= ~44 mm apart); a wrong frame (untransformed world Position)
# must be metres away.
FRAME_NN_MEDIAN_MAX_M = 0.05
FRAME_NEGATIVE_NN_MEDIAN_MIN_M = 0.5


class WriteGuard:
    """Refuses every file write / create / delete outside ``allowed`` while active (sys.addaudithook)."""

    _installed = False
    _active: "WriteGuard | None" = None
    MUTATING = ("os.remove", "os.rename", "os.rmdir", "os.mkdir", "os.symlink", "os.link", "os.truncate",
                "os.chmod", "os.utime", "shutil.rmtree", "shutil.move")
    WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND

    def __init__(self, allowed: Path) -> None:
        self.allowed = Path(allowed).resolve()
        self.violations: list[str] = []
        self.writes: list[str] = []

    def __enter__(self) -> "WriteGuard":
        if not WriteGuard._installed:
            sys.addaudithook(WriteGuard._hook)
            WriteGuard._installed = True
        WriteGuard._active = self
        return self

    def __exit__(self, *exc) -> None:
        WriteGuard._active = None

    def _inside(self, p: Any) -> bool:
        try:
            q = Path(os.fsdecode(p)).resolve()
        except (TypeError, ValueError):
            return False
        return q == self.allowed or self.allowed in q.parents

    @staticmethod
    def _hook(event: str, args: tuple) -> None:
        g = WriteGuard._active
        if g is None:
            return
        if event == "open":
            path, mode, flags = (tuple(args) + (None, None, None))[:3]
            if path is None or isinstance(path, int):
                return
            writing = (isinstance(mode, str) and any(c in mode for c in "wax+")) or \
                (isinstance(flags, int) and bool(flags & WriteGuard.WRITE_FLAGS))
            if not writing:
                return
        elif event in WriteGuard.MUTATING:
            path = args[0] if args else None
            if path is None or isinstance(path, int):
                return
        else:
            return
        if g._inside(path):
            g.writes.append(os.fsdecode(path))
            return
        g.violations.append(f"{event}: {path}")
        raise PermissionError(f"{PREFIX} read-only diagnostic refused a write outside --out: {event} {path}")


# ------------------------------------------------------------------ small helpers
def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> Any:
    with open(path, "rb") as f:
        return json.loads(f.read())


def stop(msg: str) -> None:
    raise SystemExit(f"{PREFIX} STOP {msg}")


def frac(num: int, den: int) -> float | None:
    return float(num) / float(den) if den else None


def pct(x: float | None) -> str:
    return "—" if x is None else f"{100.0 * x:.2f} %"


def canonical(d: Any) -> bytes:
    return json.dumps(d, sort_keys=True, allow_nan=False, default=lambda o: o.item() if hasattr(o, "item") else str(o)
                      ).encode()


def code_state() -> dict:
    def git(*a: str) -> str:
        return subprocess.run(["git", "-C", str(REPO), *a], check=True, capture_output=True, text=True).stdout.strip()
    return {"commit": git("rev-parse", "HEAD"), "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
            "dirty": bool(git("status", "--porcelain", "--untracked-files=no"))}


def nn_dist(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Brute-force nearest-neighbour distance from every row of ``a`` to the rows of ``b``."""
    out = np.empty(len(a), np.float64)
    chunk = max(1, int(2e7 // max(1, len(b))))
    for k in range(0, len(a), chunk):
        d = a[k:k + chunk, None, :] - b[None, :, :]
        out[k:k + chunk] = np.sqrt(np.einsum("ijk,ijk->ij", d, d).min(axis=1))
    return out


def check(rows: list, name: str, ok: bool, detail: Any) -> None:
    rows.append({"check": name, "passed": bool(ok), "detail": detail})


# ------------------------------------------------------------------ inputs
def load_inputs(c01: Path, ns1e: Path) -> dict:
    """Pins and identities.  Any mismatch is a STOP before coverage is computed."""
    inp: dict = {"c01": {"path": str(c01)}, "ns1e": {"path": str(ns1e)}}
    for rel, want in C01_PINS.items():
        got = sha256(c01 / rel)
        if got != want:
            stop(f"Controller-01 {rel} sha256 {got} != accepted {want}")
    inp["c01"]["pins"] = dict(C01_PINS)
    man = read_json(c01 / "manifest.json")
    ev_c01 = read_json(c01 / "evaluation.json")
    if man.get("control_complete") is not True or man.get("smoke"):
        stop("the Controller-01 manifest is not a complete full run")
    reach_p = c01 / "bootstrap/evaluation_only/reachable_samples.npz"
    seeds_p = c01 / "bootstrap/seeds.json"
    inp["c01"]["reachable_samples_sha256"] = sha256(reach_p)
    inp["c01"]["seeds_sha256"] = sha256(seeds_p)

    for rel, want in NS1E_PINS.items():
        got = sha256(ns1e / rel)
        if got != want:
            stop(f"NS1e {rel} sha256 {got} != accepted {want}")
    inp["ns1e"]["pins"] = dict(NS1E_PINS)
    cm = read_json(ns1e / "control/control-manifest.json")
    cfz = read_json(ns1e / "freeze/control-freeze.json")
    if cm.get("control_complete") is not True:
        stop("the NS1e control manifest is not control_complete")
    fs_rel = cm["final_scene_state"]
    fs_sha = sha256(ns1e / fs_rel)
    if fs_sha != cm["final_scene_state_sha256"] or fs_sha != cfz["files"][fs_rel]:
        stop("the NS1e final scene state does not verify against the control manifest / freeze")
    inp["ns1e"]["final_scene_state"] = {"path": fs_rel, "sha256": fs_sha}
    final = read_json(ns1e / fs_rel)
    ev_ns1e = read_json(ns1e / "evaluation/evaluation.json")
    cov_p = ns1e / "evaluation/coverage.npz"
    inp["ns1e"]["coverage_npz_sha256"] = sha256(cov_p)

    ref = ev_ns1e["reference"]
    exr = Path(ref["path"])
    if ref["sha256"] != SP.B1_EXR_SHA256 or sha256(exr) != SP.B1_EXR_SHA256:
        stop("the Breadth-1 reference EXR is not the accepted one used by NS1e")
    inp["breadth1"] = {"exr": str(exr), "sha256": SP.B1_EXR_SHA256, "cell_deg": B1S.CELL_DEG,
                       "raster": [B1S.WIDTH, B1S.HEIGHT]}
    ev_sha = sha256(Path(EV.__file__))
    if ev_sha != EVALUATOR_SHA256:
        stop(f"classroom_oracle1_eval.py sha256 {ev_sha} != the sealed pin {EVALUATOR_SHA256}")
    if float(EV.public.FUSION["association_radius_m"]) != RADIUS_M or float(SP.COVERAGE_RADIUS_M) != RADIUS_M:
        stop("the accepted coverage radius is not 12 mm on both sides")
    inp["evaluator"] = {"module": "tools/classroom_oracle1_eval.py", "function": "_covered", "sha256": ev_sha,
                        "radius_m": RADIUS_M}
    return {"inp": inp, "man": man, "ev_c01": ev_c01, "final": final, "ev_ns1e": ev_ns1e, "cov_p": cov_p,
            "reach_p": reach_p, "seeds_p": seeds_p, "exr": exr}


# ------------------------------------------------------------------ the computation
def compute(c01: Path, ns1e: Path) -> dict:
    t0 = time.perf_counter()
    L = load_inputs(c01, ns1e)
    man, ev_c01, final, ev_ns1e = L["man"], L["ev_c01"], L["final"], L["ev_ns1e"]
    ents = final["entities"]
    t_inputs = time.perf_counter() - t0

    # ---- ids (derived, never hard-coded)
    old_ids = sorted(int(o["instance_id"]) for o in man["objects"])
    if old_ids != sorted(int(x) for x in man["localized_object_ids"]):
        stop("Controller-01 attempted objects != localized_object_ids")
    new_ids = sorted(int(k) for k in ents)
    if new_ids != sorted(int(k) for k in ev_ns1e["per_entity"]) or len(new_ids) != 10:
        stop("NS1e scheduler entities != the ten evaluated entities")
    common = sorted(set(old_ids) & set(new_ids))
    if not common:
        stop("no common id")
    obj_by_id = {int(o["instance_id"]): o for o in man["objects"]}
    c01_eval_row = {int(r["instance_id"]): r for r in ev_c01["objects"]}

    # ---- frame guard (metadata / provenance)
    fg: list = []
    seeds = read_json(L["seeds_p"])
    hr_c01, ho_c01 = np.asarray(seeds["head_R_wh"], np.float64), np.asarray(seeds["head_origin_w_m"], np.float64)
    cal_ref = ev_ns1e["reference"]["head_pose_source"]
    cal_ns = read_json(CORE.resolve(cal_ref, ns1e))
    hr, ho = np.asarray(cal_ns["head_R_wh"], np.float64), np.asarray(cal_ns["head_origin_w_m"], np.float64)
    check(fg, "F1 head pose: Controller-01 seeds.json == the NS1e evaluation head pose (bitwise)",
          np.array_equal(hr, hr_c01) and np.array_equal(ho, ho_c01),
          {"head_R_wh": hr_c01.tolist(), "head_origin_w_m": ho_c01.tolist(), "ns1e_source": cal_ref})

    bad_cal: list[str] = []
    n_c01_cal = n_ns_cal = 0
    for i in common:
        for k in range(int(obj_by_id[i]["fixation_count"])):
            p = c01 / f"objects/instance_{i:04d}/acquisitions/fix_{k:02d}/calibration.json"
            c = read_json(p)
            n_c01_cal += 1
            if not (np.array_equal(np.asarray(c["head_R_wh"]), hr_c01)
                    and np.array_equal(np.asarray(c["head_origin_w_m"]), ho_c01)
                    and c.get("map_frame") == H_FRAME
                    and [e["centre_h_m"] for e in c["eyes"]] == EYE_CENTRES_H):
                bad_cal.append(str(p))
        for look in ents[str(i)]["looks"]:
            p = CORE.resolve(look["calibration"], ns1e)
            c = read_json(p)
            n_ns_cal += 1
            if not (np.array_equal(np.asarray(c["head_R_wh"]), hr_c01)
                    and np.array_equal(np.asarray(c["head_origin_w_m"]), ho_c01)
                    and c.get("map_frame") == H_FRAME
                    and [e["centre_h_m"] for e in c["eyes"]] == EYE_CENTRES_H):
                bad_cal.append(str(p))
    check(fg, "F2 every look that built a common-id map (both runs): same head pose, map_frame H, eye centres",
          not bad_cal, {"controller01_calibrations": n_c01_cal, "ns1e_calibrations": n_ns_cal,
                        "map_frame": H_FRAME, "mismatches": bad_cal})

    with np.load(L["reach_p"], allow_pickle=False) as z:  # exactly as classroom_oracle1_eval.main reads it
        truth_ids = np.asarray(z["instance_id"], np.int32)
        truth_xyz = np.asarray(z["xyz_h"], np.float64)
        truth_dir = np.asarray(z["direction_h"], np.float64)
        truth_ang = np.asarray(z["yaw_pitch_deg"], np.float64)
    finite_ref = bool(np.isfinite(truth_xyz).all() and truth_xyz.ndim == 2 and truth_xyz.shape[1] == 3)
    u = truth_xyz / np.linalg.norm(truth_xyz, axis=1, keepdims=True)
    ang_err = np.degrees(np.arccos(np.clip(np.einsum("ij,ij->i", u, truth_dir / np.linalg.norm(
        truth_dir, axis=1, keepdims=True)), -1.0, 1.0)))
    yaw_c, pitch_c = B1S.yaw_pitch_deg(truth_dir)
    dyaw = np.abs((yaw_c - truth_ang[:, 0] + 180.0) % 360.0 - 180.0)
    dpitch = np.abs(pitch_c - truth_ang[:, 1])
    dom_y, dom_p = B1S.DOMAIN_YAW_DEG, B1S.DOMAIN_PITCH_DEG
    in_dom = ((truth_ang[:, 0] >= dom_y[0]) & (truth_ang[:, 0] <= dom_y[1])
              & (truth_ang[:, 1] >= dom_p[0]) & (truth_ang[:, 1] <= dom_p[1]))
    check(fg, "F3 historical reference: finite H-frame XYZ on cyclopean rays from the head origin; stored yaw/pitch "
              "== the Breadth-1 convention; all inside the old domain",
          finite_ref and float(ang_err.max()) < 1e-3 and float(dyaw.max()) < 1e-3 and float(dpitch.max()) < 1e-3
          and bool(in_dom.all()) and list(seeds["controller_domain_deg"]["yaw"]) == list(dom_y)
          and list(seeds["controller_domain_deg"]["pitch"]) == list(dom_p),
          {"samples": int(len(truth_ids)), "max_ray_angle_err_deg": float(ang_err.max()),
           "max_dyaw_deg": float(dyaw.max()), "max_dpitch_deg": float(dpitch.max()),
           "outside_old_domain": int((~in_dom).sum()), "controller_domain_deg": seeds["controller_domain_deg"]})

    ex = BG1.extract_exr(L["exr"])
    inst, pos = ex["instance"], ex["position_w"]
    if inst.shape != (B1S.HEIGHT, B1S.WIDTH) or not ex["index_integral"]:
        stop("the Breadth-1 raster is not 720 x 360 with an integral Object Index")
    orient = BG1.orientation_residuals(pos, inst > 0, hr_c01, ho_c01)
    check(fg, "F4 Breadth-1 orientation test with the Controller-01 head pose: 0 authored cells outside their cell",
          orient["outside"] == 0, orient)

    # ---- maps
    maps_old: dict[int, np.ndarray] = {}
    maps_new: dict[int, np.ndarray] = {}
    map_info: dict[str, dict] = {}
    for i in common:
        mp = c01 / f"objects/instance_{i:04d}/final_map.npz"
        with np.load(mp, allow_pickle=False) as z:
            raw_old = np.asarray(z["xyz_h"])
        maps_old[i] = EV._load_map(mp)                       # the accepted loader (finite rows)
        rec = ents[str(i)]
        np_ = CORE.resolve(rec["map"]["path"], ns1e)
        if sha256(np_) != rec["map"]["sha256"]:
            stop(f"NS1e final map of {i} differs from its frozen record")
        raw_new = CORE.map_xyz(rec, ns1e)
        maps_new[i] = raw_new[np.isfinite(raw_new).all(axis=1)]  # exactly as NS1e evaluate
        map_info[str(i)] = {
            "controller01_final_map": {"path": str(mp.relative_to(c01)), "sha256": sha256(mp),
                                       "surfels": int(len(maps_old[i])), "rows": int(len(raw_old)),
                                       "manifest_final_map_surfels": int(obj_by_id[i]["final_map_surfels"])},
            "ns1e_final_map": {"path": rec["map"]["path"], "sha256": rec["map"]["sha256"],
                               "surfels": int(len(maps_new[i])), "rows": int(len(raw_new)),
                               "record_surfels": int(rec["map"]["surfels"])}}
    dims_ok = all(m["controller01_final_map"]["surfels"] == m["controller01_final_map"]["rows"]
                  == m["controller01_final_map"]["manifest_final_map_surfels"]
                  and m["ns1e_final_map"]["surfels"] == m["ns1e_final_map"]["rows"] == m["ns1e_final_map"]["record_surfels"]
                  for m in map_info.values())
    check(fg, "F5 final maps: (N, 3) finite XYZ, surfel counts equal the run records", dims_ok, map_info)

    # ---- frame guard (geometry): the historical samples lie on the Breadth-1 surface only in the shared frame
    nn_rows = {}
    nn_all, nn_neg_all = [], []
    for i in common:
        mask = CORE.reference_mask(inst, pos, i)
        b1_h = CORE.head_points(pos[mask], hr, ho)
        b1_w = np.asarray(pos[mask], np.float64)               # negative control: untransformed world Position
        ref = truth_xyz[truth_ids == i]
        d = nn_dist(ref, b1_h)
        dn = nn_dist(ref, b1_w)
        nn_all.append(d)
        nn_neg_all.append(dn)
        nn_rows[str(i)] = {"samples": int(len(ref)), "median_m": float(np.median(d)),
                           "p90_m": float(np.percentile(d, 90)), "negative_control_median_m": float(np.median(dn))}
    nn_all_a, nn_neg_a = np.concatenate(nn_all), np.concatenate(nn_neg_all)
    check(fg, "F6 geometric cross-check: historical samples -> nearest same-id Breadth-1 H point "
              f"(median < {FRAME_NN_MEDIAN_MAX_M} m); untransformed world negative control (median > "
              f"{FRAME_NEGATIVE_NN_MEDIAN_MIN_M} m)",
          float(np.median(nn_all_a)) < FRAME_NN_MEDIAN_MAX_M
          and float(np.median(nn_neg_a)) > FRAME_NEGATIVE_NN_MEDIAN_MIN_M,
          {"median_m": float(np.median(nn_all_a)), "p90_m": float(np.percentile(nn_all_a, 90)),
           "negative_control_median_m": float(np.median(nn_neg_a)), "per_id": nn_rows})
    if not all(r["passed"] for r in fg):
        failed = [r["check"] for r in fg if not r["passed"]]
        stop(f"coordinate-frame guard failed before coverage: {failed}")
    t_guard = time.perf_counter() - t0 - t_inputs

    # ---- coverage
    w = B1S.row_weights()
    yc, pc = B1S.yaw_centers_deg(), B1S.pitch_centers_deg()
    in_domain = ((yc[None, :] >= dom_y[0]) & (yc[None, :] <= dom_y[1])
                 & (pc[:, None] >= dom_p[0]) & (pc[:, None] <= dom_p[1]))   # the Breadth-1 definition
    ka: list = []
    with np.load(L["cov_p"], allow_pickle=False) as z:
        ns1e_cov = {k: np.asarray(z[k]) for k in z.files}
    primary, scope, split = [], [], []
    agg = {k: 0 for k in ("ref", "A", "C", "cells", "B", "D", "in_cells", "out_cells", "B_in", "B_out", "D_in",
                          "D_out")}
    aggw = {k: 0.0 for k in ("omega", "B", "D", "in", "out", "B_in", "B_out", "D_in", "D_out")}
    for i in common:
        ref_old = truth_xyz[truth_ids == i]
        cov_a = EV._covered(ref_old, maps_old[i], RADIUS_M)
        cov_c = EV._covered(ref_old, maps_new[i], RADIUS_M)
        row_h = c01_eval_row[i]
        check(ka, f"K1 id {i}: Controller-01 map on the historical reference reproduces the accepted "
                  "Controller-01 evaluation.json",
              int(len(ref_old)) == int(row_h["reachable_samples"]) and int(cov_a.sum()) == int(row_h["covered_samples"]),
              {"reference": int(len(ref_old)), "covered": int(cov_a.sum()),
               "accepted_reference": int(row_h["reachable_samples"]), "accepted_covered": int(row_h["covered_samples"])})
        n = int(len(ref_old))
        primary.append({"id": i, "historical_reference_samples": n,
                        "controller01_covered": int(cov_a.sum()), "controller01_fraction": frac(int(cov_a.sum()), n),
                        "ns1e_covered": int(cov_c.sum()), "ns1e_fraction": frac(int(cov_c.sum()), n),
                        "delta_pp": 100.0 * (frac(int(cov_c.sum()), n) - frac(int(cov_a.sum()), n)),
                        "controller01_final_surfels": int(len(maps_old[i])),
                        "ns1e_final_surfels": int(len(maps_new[i]))})
        agg["ref"] += n
        agg["A"] += int(cov_a.sum())
        agg["C"] += int(cov_c.sum())

        mask = CORE.reference_mask(inst, pos, i)
        rr, cc = np.nonzero(mask)
        ref_b1 = CORE.head_points(pos[mask], hr, ho)
        cov_b = EV._covered(ref_b1, maps_old[i], RADIUS_M)
        cov_d = EV._covered(ref_b1, maps_new[i], RADIUS_M)
        cells_ok = np.array_equal(np.stack([rr, cc], 1).astype(np.int32), ns1e_cov[f"e{i:05d}_cells"])
        cov_ok = np.array_equal(cov_d, ns1e_cov[f"e{i:05d}_covered"])
        pe = ev_ns1e["per_entity"][str(i)]
        check(ka, f"K2 id {i}: NS1e map on Breadth-1 reproduces NS1e evaluation/coverage.npz bitwise",
              cells_ok and cov_ok and int(cov_d.sum()) == int(pe["covered_cells"])
              and int(mask.sum()) == int(pe["reference_cells"]),
              {"cells_equal": cells_ok, "covered_equal": cov_ok, "covered": int(cov_d.sum()),
               "accepted_covered": int(pe["covered_cells"]), "reference_cells": int(mask.sum())})
        wi = w[rr]
        ins = in_domain[rr, cc]
        ncell = int(mask.sum())
        om = float(wi.sum())
        scope.append({"id": i,
                      "A_controller01_vs_old_local": frac(int(cov_a.sum()), n),
                      "C_ns1e_vs_old_local": frac(int(cov_c.sum()), n),
                      "B_controller01_vs_full_sphere": frac(int(cov_b.sum()), ncell),
                      "D_ns1e_vs_full_sphere": frac(int(cov_d.sum()), ncell),
                      "B_weighted": float(wi[cov_b].sum()) / om, "D_weighted": float(wi[cov_d].sum()) / om,
                      "old_local_samples": n, "full_sphere_cells": ncell, "full_sphere_sr": om,
                      "B_covered_cells": int(cov_b.sum()), "D_covered_cells": int(cov_d.sum())})

        def part(sel: np.ndarray) -> dict:
            k = int(sel.sum())
            return {"cells": k, "sr": float(wi[sel].sum()),
                    "controller01_covered": int((cov_b & sel).sum()), "ns1e_covered": int((cov_d & sel).sum()),
                    "controller01_fraction": frac(int((cov_b & sel).sum()), k),
                    "ns1e_fraction": frac(int((cov_d & sel).sum()), k)}
        split.append({"id": i, "inside_old_domain": part(ins), "outside_old_domain": part(~ins),
                      "all": part(np.ones_like(ins))})
        agg["cells"] += ncell
        agg["B"] += int(cov_b.sum())
        agg["D"] += int(cov_d.sum())
        agg["in_cells"] += int(ins.sum())
        agg["out_cells"] += int((~ins).sum())
        agg["B_in"] += int((cov_b & ins).sum())
        agg["B_out"] += int((cov_b & ~ins).sum())
        agg["D_in"] += int((cov_d & ins).sum())
        agg["D_out"] += int((cov_d & ~ins).sum())
        aggw["omega"] += om
        aggw["B"] += float(wi[cov_b].sum())
        aggw["D"] += float(wi[cov_d].sum())
        aggw["in"] += float(wi[ins].sum())
        aggw["out"] += float(wi[~ins].sum())
        aggw["B_in"] += float(wi[cov_b & ins].sum())
        aggw["B_out"] += float(wi[cov_b & ~ins].sum())
        aggw["D_in"] += float(wi[cov_d & ins].sum())
        aggw["D_out"] += float(wi[cov_d & ~ins].sum())
    t_cov = time.perf_counter() - t0 - t_inputs - t_guard

    # ---- descriptive look geometry (where each map's looks pointed; H yaw/pitch of the gaze)
    def inside(g) -> bool:
        return dom_y[0] <= g[0] <= dom_y[1] and dom_p[0] <= g[1] <= dom_p[1]
    looks = {}
    for i in common:
        g_old = [[float(v) for v in t["gaze_deg"]] for t in obj_by_id[i]["trajectory"]]
        g_new = [[float(v) for v in read_json(CORE.resolve(lk["calibration"], ns1e))["gaze_yaw_pitch_deg"]]
                 for lk in ents[str(i)]["looks"]]
        looks[str(i)] = {
            "controller01": {"looks": len(g_old), "inside_old_domain": sum(inside(g) for g in g_old),
                             "yaw_range_deg": [min(g[0] for g in g_old), max(g[0] for g in g_old)],
                             "pitch_range_deg": [min(g[1] for g in g_old), max(g[1] for g in g_old)]},
            "ns1e": {"looks": len(g_new), "inside_old_domain": sum(inside(g) for g in g_new),
                     "yaw_range_deg": [min(g[0] for g in g_new), max(g[0] for g in g_new)],
                     "pitch_range_deg": [min(g[1] for g in g_new), max(g[1] for g in g_new)]}}

    # ---- descriptive support geometry: how far each map is from the historical samples, and how much of each
    # map lies inside the old domain (cyclopean direction of the surfel from the head origin, H frame)
    support = {}
    for i in common:
        ref_old = truth_xyz[truth_ids == i]
        row = {}
        for name, mp in (("controller01", maps_old[i]), ("ns1e", maps_new[i])):
            dd = nn_dist(ref_old, mp)
            yaw_m, pitch_m = B1S.yaw_pitch_deg(mp)
            ins_m = (yaw_m >= dom_y[0]) & (yaw_m <= dom_y[1]) & (pitch_m >= dom_p[0]) & (pitch_m <= dom_p[1])
            row[name] = {"historical_sample_to_map_distance_m": {
                             "min": float(dd.min()), "p10": float(np.percentile(dd, 10)),
                             "median": float(np.median(dd)), "max": float(dd.max()),
                             "within_12mm": int((dd <= RADIUS_M).sum())},
                         "map_surfels": int(len(mp)), "map_surfels_inside_old_domain": int(ins_m.sum()),
                         "map_yaw_range_deg": [float(yaw_m.min()), float(yaw_m.max())],
                         "map_pitch_range_deg": [float(pitch_m.min()), float(pitch_m.max())]}
        support[str(i)] = row
    for i in common:   # the brute-force distance must agree with _covered (independent implementation)
        p_ = next(x for x in primary if x["id"] == i)
        check(ka, f"K3 id {i}: brute-force distances <= 12 mm agree with _covered for both maps",
              support[str(i)]["controller01"]["historical_sample_to_map_distance_m"]["within_12mm"]
              == p_["controller01_covered"]
              and support[str(i)]["ns1e"]["historical_sample_to_map_distance_m"]["within_12mm"] == p_["ns1e_covered"],
              {"controller01": [support[str(i)]["controller01"]["historical_sample_to_map_distance_m"]["within_12mm"],
                                p_["controller01_covered"]],
               "ns1e": [support[str(i)]["ns1e"]["historical_sample_to_map_distance_m"]["within_12mm"],
                        p_["ns1e_covered"]]})

    micro_primary = {"historical_reference_samples": agg["ref"],
                     "controller01_covered": agg["A"], "controller01_fraction": frac(agg["A"], agg["ref"]),
                     "ns1e_covered": agg["C"], "ns1e_fraction": frac(agg["C"], agg["ref"]),
                     "delta_pp": 100.0 * (frac(agg["C"], agg["ref"]) - frac(agg["A"], agg["ref"]))}
    micro_scope = {"A_controller01_vs_old_local": frac(agg["A"], agg["ref"]),
                   "C_ns1e_vs_old_local": frac(agg["C"], agg["ref"]),
                   "B_controller01_vs_full_sphere": frac(agg["B"], agg["cells"]),
                   "D_ns1e_vs_full_sphere": frac(agg["D"], agg["cells"]),
                   "B_weighted": aggw["B"] / aggw["omega"], "D_weighted": aggw["D"] / aggw["omega"],
                   "old_local_samples": agg["ref"], "full_sphere_cells": agg["cells"],
                   "full_sphere_sr": aggw["omega"], "B_covered_cells": agg["B"], "D_covered_cells": agg["D"]}
    micro_split = {
        "inside_old_domain": {"cells": agg["in_cells"], "sr": aggw["in"],
                              "controller01_covered": agg["B_in"], "ns1e_covered": agg["D_in"],
                              "controller01_fraction": frac(agg["B_in"], agg["in_cells"]),
                              "ns1e_fraction": frac(agg["D_in"], agg["in_cells"]),
                              "controller01_weighted": aggw["B_in"] / aggw["in"] if aggw["in"] else None,
                              "ns1e_weighted": aggw["D_in"] / aggw["in"] if aggw["in"] else None},
        "outside_old_domain": {"cells": agg["out_cells"], "sr": aggw["out"],
                               "controller01_covered": agg["B_out"], "ns1e_covered": agg["D_out"],
                               "controller01_fraction": frac(agg["B_out"], agg["out_cells"]),
                               "ns1e_fraction": frac(agg["D_out"], agg["out_cells"]),
                               "controller01_weighted": aggw["B_out"] / aggw["out"] if aggw["out"] else None,
                               "ns1e_weighted": aggw["D_out"] / aggw["out"] if aggw["out"] else None},
        "all": {"cells": agg["cells"], "sr": aggw["omega"], "controller01_covered": agg["B"],
                "ns1e_covered": agg["D"], "controller01_fraction": frac(agg["B"], agg["cells"]),
                "ns1e_fraction": frac(agg["D"], agg["cells"]),
                "controller01_weighted": aggw["B"] / aggw["omega"], "ns1e_weighted": aggw["D"] / aggw["omega"]}}

    result = {
        "ids": {"old_ids_controller01_localized": old_ids, "new_ids_ns1e_scheduler": new_ids, "common_ids": common},
        "frame_guard": fg,
        "known_answers": ka,
        "primary_apples_to_apples": {
            "reference": "Controller-01 bootstrap/evaluation_only/reachable_samples.npz (dense 0.25-degree cyclopean "
                         "first-hit samples in the frozen Controller-01 angular domain)",
            "per_id": primary, "micro_common_ids": micro_primary},
        "scope_matrix_2x2": {
            "note": "A / C: fractions of the historical 0.25-degree samples; B / D: fractions of Breadth-1 0.5-degree "
                    "cells (and solid-angle weighted). Raw counts of the two references are not comparable.",
            "per_id": scope, "micro_common_ids": micro_scope},
        "domain_split_breadth1": {
            "definition": "Breadth-1 cell centre yaw in [-25, +25] deg and pitch in [-20, +20] deg (closed), H frame",
            "per_id": split, "micro_common_ids": micro_split},
        "look_geometry_descriptive": looks,
        "support_geometry_descriptive": support,
    }
    passed = all(r["passed"] for r in fg + ka)
    return {"inputs": L["inp"], "result": result, "passed": passed,
            "timing_s": {"inputs_and_pins": t_inputs, "frame_guard": t_guard, "coverage": t_cov,
                         "total": time.perf_counter() - t0}}


# ------------------------------------------------------------------ figure (Visual Language 1 palette, PIL)
def figure(res: dict, path: Path) -> None:
    from PIL import Image, ImageDraw
    import style as S

    r = res["result"]
    common = r["ids"]["common_ids"]
    W, H = 2200, 1330
    img = Image.new("RGB", (W, H), S.SURFACE)
    d = ImageDraw.Draw(img)
    c01c, nsc = S.OI_BLUE, S.OI_ORANGE
    S.text(d, (60, 34), "NS1e apples-to-apples coverage — DIAGNOSTIC, REVIEW PENDING", size=S.T_TITLE, bold=True,
           outline=None)
    S.text(d, (60, 78), "Final persistent maps only; covered iff within 12 mm of a surfel (accepted _covered). "
                        f"Common ids (derived): {', '.join(map(str, common))}.  REFERENCE / EVALUATION: oracle "
                        "first-hit references, read after control.", size=S.T_SMALL, fill=S.INK2, outline=None)

    def tint(c, a=0.25):
        return tuple(int(round(255 - a * (255 - v))) for v in c)

    def bar(x0, x1, y_base, y_top, color, hatched):
        if y_top > y_base - 2:            # zero: a thin baseline tick so the bar is visibly present but empty
            d.line([x0, y_base, x1, y_base], fill=color, width=3)
            return
        rad = int(max(0, min(4, (y_base - y_top) / 2, (x1 - x0) / 2)))
        if hatched:
            d.rounded_rectangle([x0, y_top, x1, y_base], radius=rad, fill=tint(color), outline=color, width=2)
            if y_base - y_top > 6:
                S.hatch(img, (x0 + 2, y_top + 2, x1 - 2, y_base - 2), color, spacing=10, width=2)
        else:
            d.rounded_rectangle([x0, y_top, x1, y_base], radius=rad, fill=color)

    def axes(px0, py0, px1, py1, title):
        S.text(d, (px0 - 90, py0 - 78), title, size=S.T_HEAD, bold=True, outline=None)
        for v in range(0, 101, 25):
            y = py1 - (py1 - py0) * v / 100.0
            d.line([px0, y, px1, y], fill=S.GRID, width=1)
            S.text(d, (px0 - 12, y), f"{v} %", size=S.T_SMALL, fill=S.MUTED, outline=None, anchor="rm")
        d.line([px0, py1, px1, py1], fill=S.INK2, width=2)

    def value(x, y_top, y_base, f):
        S.text(d, (x, min(y_top, y_base) - 8), "—" if f is None else f"{100 * f:.1f}", size=S.T_SMALL, fill=S.INK,
               outline=None, anchor="md")

    # Panel 1: the 2 x 2 per id and the micro aggregate
    px0, py0, px1, py1 = 150, 300, 1450, 1030
    axes(px0, py0, px1, py1, "Coverage of each id: two maps × two references")
    groups = [(str(s["id"]), s) for s in r["scope_matrix_2x2"]["per_id"]] + \
        [("micro (common ids)", r["scope_matrix_2x2"]["micro_common_ids"])]
    gw = (px1 - px0) / len(groups)
    bw = gw * 0.16
    for gi, (label, s) in enumerate(groups):
        gx = px0 + gi * gw + gw * 0.10
        bars = [("A_controller01_vs_old_local", c01c, False), ("C_ns1e_vs_old_local", nsc, False),
                ("B_controller01_vs_full_sphere", c01c, True), ("D_ns1e_vs_full_sphere", nsc, True)]
        for bi, (key, col, hat) in enumerate(bars):
            x0 = gx + bi * (bw + 2) + (gw * 0.06 if bi >= 2 else 0)
            f = s[key] or 0.0
            yt = py1 - (py1 - py0) * f
            bar(x0, x0 + bw, py1, yt, col, hat)
            value(x0 + bw / 2, yt, py1, s[key])
        S.text(d, (px0 + gi * gw + gw / 2, py1 + 30), label, size=S.T_BODY, bold=True, outline=None, anchor="ma")
        S.text(d, (px0 + gi * gw + gw / 2, py1 + 62), f"old ref N = {s['old_local_samples']:,}",
               size=S.T_SMALL, fill=S.MUTED, outline=None, anchor="ma")
        S.text(d, (px0 + gi * gw + gw / 2, py1 + 88), f"sphere cells = {s['full_sphere_cells']:,}",
               size=S.T_SMALL, fill=S.MUTED, outline=None, anchor="ma")

    # Panel 2: Breadth-1 domain split (micro over the common ids)
    qx0, qy0, qx1, qy1 = 1620, 300, 2140, 1030
    axes(qx0, qy0, qx1, qy1, "Breadth-1 cells: old domain split")
    ms = r["domain_split_breadth1"]["micro_common_ids"]
    parts = [("inside", "inside_old_domain"), ("outside", "outside_old_domain"), ("all", "all")]
    gw2 = (qx1 - qx0) / len(parts)
    bw2 = gw2 * 0.30
    for gi, (label, key) in enumerate(parts):
        gx = qx0 + gi * gw2 + gw2 * 0.18
        for bi, (fk, col) in enumerate((("controller01_fraction", c01c), ("ns1e_fraction", nsc))):
            x0 = gx + bi * (bw2 + 2)
            f = ms[key][fk] or 0.0
            yt = qy1 - (qy1 - qy0) * f
            bar(x0, x0 + bw2, qy1, yt, col, True)
            value(x0 + bw2 / 2, yt, qy1, ms[key][fk])
        S.text(d, (qx0 + gi * gw2 + gw2 / 2, qy1 + 30), label, size=S.T_BODY, bold=True, outline=None, anchor="ma")
        S.text(d, (qx0 + gi * gw2 + gw2 / 2, qy1 + 62), f"{ms[key]['cells']:,} cells", size=S.T_SMALL,
               fill=S.MUTED, outline=None, anchor="ma")

    # Legend (identity never by colour alone: series named, reference by texture)
    ly = 140
    items = [(c01c, False, "Controller-01 final map · old local ref (A)"),
             (nsc, False, "NS1e final map · old local ref (C)"),
             (c01c, True, "Controller-01 final map · Breadth-1 sphere ref (B)"),
             (nsc, True, "NS1e final map · Breadth-1 sphere ref (D)")]
    lx = 60
    for col, hat, lab in items:
        bar(lx, lx + 34, ly + 26, ly, col, hat)
        bb = S.text(d, (lx + 46, ly + 13), lab, size=S.T_SMALL, outline=None, anchor="lm")
        lx = bb[2] + 44
    pa = r["primary_apples_to_apples"]["micro_common_ids"]
    S.text(d, (60, H - 150), f"PRIMARY (same {pa['historical_reference_samples']:,} historical samples): "
                             f"Controller-01 {pct(pa['controller01_fraction'])}  ·  NS1e {pct(pa['ns1e_fraction'])}  ·  "
                             f"Δ {pa['delta_pp']:+.2f} pp", size=S.T_BODY, bold=True, outline=None)
    sup = r["support_geometry_descriptive"]
    near = min(sup[k]["ns1e"]["historical_sample_to_map_distance_m"]["min"] for k in sup)
    ins = sum(sup[k]["ns1e"]["map_surfels_inside_old_domain"] for k in sup)
    S.text(d, (60, H - 120 + 40), f"Nearest NS1e surfel to any historical sample: {near:.2f} m.  NS1e surfels inside "
                                  f"the old domain: {ins}.", size=S.T_SMALL, fill=S.INK2, outline=None)
    S.text(d, (60, H - 76 + 34), "Old domain: cell-centre yaw ±25°, pitch ±20° (Breadth-1 definition). Fractions only; "
                            "raw counts of the 0.25° and 0.5° references are not comparable.", size=S.T_SMALL,
           fill=S.INK2, outline=None)
    img.save(path, format="PNG", optimize=False)


# ------------------------------------------------------------------ table text (for the console)
def summary_lines(res: dict) -> list[str]:
    r = res["result"]
    out = [f"{PREFIX} COMMON_IDS {r['ids']['common_ids']}"]
    for p in r["primary_apples_to_apples"]["per_id"]:
        out.append(f"{PREFIX} PRIMARY id {p['id']}: N {p['historical_reference_samples']}  C01 "
                   f"{pct(p['controller01_fraction'])}  NS1e {pct(p['ns1e_fraction'])}  delta {p['delta_pp']:+.2f} pp")
    m = r["primary_apples_to_apples"]["micro_common_ids"]
    out.append(f"{PREFIX} PRIMARY micro: N {m['historical_reference_samples']}  C01 {pct(m['controller01_fraction'])}"
               f"  NS1e {pct(m['ns1e_fraction'])}  delta {m['delta_pp']:+.2f} pp")
    s = r["scope_matrix_2x2"]["micro_common_ids"]
    out.append(f"{PREFIX} 2x2 micro: A {pct(s['A_controller01_vs_old_local'])}  B "
               f"{pct(s['B_controller01_vs_full_sphere'])}  C {pct(s['C_ns1e_vs_old_local'])}  D "
               f"{pct(s['D_ns1e_vs_full_sphere'])}")
    ms = r["domain_split_breadth1"]["micro_common_ids"]
    for k in ("inside_old_domain", "outside_old_domain", "all"):
        out.append(f"{PREFIX} split {k}: cells {ms[k]['cells']}  C01 {pct(ms[k]['controller01_fraction'])}  NS1e "
                   f"{pct(ms[k]['ns1e_fraction'])}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--c01-run", required=True, type=Path, help="the accepted Controller-01 full run")
    ap.add_argument("--ns1e-run", required=True, type=Path, help="the canonical NS1e run")
    ap.add_argument("--out", required=True, type=Path, help="output directory (the only place written)")
    ap.add_argument("--no-figure", action="store_true")
    args = ap.parse_args()
    c01, ns1e, out = args.c01_run.resolve(), args.ns1e_run.resolve(), args.out.resolve()
    for p in (c01, ns1e):
        if out == p or p in out.parents or out in p.parents:
            stop(f"--out must lie outside the input runs: {out}")
    cs = code_state()
    t0 = time.perf_counter()
    out.mkdir(parents=True, exist_ok=True)
    with WriteGuard(out) as g:
        run1 = compute(c01, ns1e)
        run2 = compute(c01, ns1e)
        dig1 = hashlib.sha256(canonical(run1["result"])).hexdigest()
        dig2 = hashlib.sha256(canonical(run2["result"])).hexdigest()
        det = {"check": "D1 the whole computation run twice gives identical numbers", "passed": dig1 == dig2,
               "detail": {"result_digest_run1": dig1, "result_digest_run2": dig2}}
        passed = run1["passed"] and run2["passed"] and det["passed"]
        doc = {"schema": SCHEMA, "status": STATUS, "truth": "REFERENCE / EVALUATION (post-control diagnostic)",
               "question": "Does the final NS1e persistent reconstruction cover the SAME historical Controller-01 "
                           "reachable surface nearly as well as the old Controller-01 reconstruction?",
               "code": cs, "inputs": run1["inputs"], "coverage_definition": {
                   "function": "classroom_oracle1_eval._covered (exact Euclidean, deterministic spatial hash)",
                   "radius_m": RADIUS_M, "maps": "final persistent surface maps only (no memory, no effective "
                                                 "geometry, no PLY)"},
               **run1["result"], "determinism": det, "all_checks_passed": passed,
               "checks_summary": {"frame_guard": f"{sum(r['passed'] for r in run1['result']['frame_guard'])}/"
                                                 f"{len(run1['result']['frame_guard'])}",
                                  "known_answers": f"{sum(r['passed'] for r in run1['result']['known_answers'])}/"
                                                   f"{len(run1['result']['known_answers'])}",
                                  "determinism": "1/1" if det["passed"] else "0/1"},
               "runtime_s": {"run1": run1["timing_s"], "run2": run2["timing_s"]}}
        if not args.no_figure:
            figure(run1, out / "comparison.png")
            doc["figure"] = {"path": "comparison.png", "sha256": sha256(out / "comparison.png")}
        doc["runtime_s"]["wall_total"] = time.perf_counter() - t0
        (out / "comparison.json").write_text(json.dumps(doc, indent=1, sort_keys=True, allow_nan=False,
                                                        default=lambda o: o.item() if hasattr(o, "item") else str(o))
                                             + "\n")
    if g.violations:
        stop(f"write guard violations: {g.violations}")
    for line in summary_lines(run1):
        print(line)
    print(f"{PREFIX} checks frame {doc['checks_summary']['frame_guard']}  known answers "
          f"{doc['checks_summary']['known_answers']}  determinism {doc['checks_summary']['determinism']}  "
          f"wall {doc['runtime_s']['wall_total']:.1f} s")
    print(f"{PREFIX} comparison.json {sha256(out / 'comparison.json')}")
    if not passed:
        raise SystemExit(f"{PREFIX} FAIL a check failed (see comparison.json)")
    print(f"{PREFIX} COMPLETE {STATUS}")


if __name__ == "__main__":
    main()
