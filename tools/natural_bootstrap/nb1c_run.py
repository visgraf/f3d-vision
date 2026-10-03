"""Natural Bootstrap-1c: RGB candidate gaze (run order and truth boundary).

Contract: docs/natural-bootstrap/nb1c-rgb-candidate-gaze-contract.md.

    .venv/bin/python tools/natural_bootstrap/nb1c_run.py synthetic --run RUN
    .venv/bin/python tools/natural_bootstrap/nb1c_run.py select    --run RUN
    .venv/bin/python tools/natural_bootstrap/nb1c_run.py freeze    --run RUN
    .venv/bin/python tools/natural_bootstrap/nb1c_run.py evaluate  --run RUN
    .venv/bin/python tools/natural_bootstrap/nb1c_run.py visualize --run RUN --visuals VIS

The two data paths run under the accepted ``nb1a_guard.OpenGuard``:
- ``select`` reads only the pinned coarse RGB proxy;
- ``evaluate`` reads the pinned NB1a / NB1b products only after it has verified the RGB gaze freeze.
No scene observation, no Blender process and no controller run.  No gaze is executed.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))

import nb1c_attention as AT  # noqa: E402
import nb1c_spec as SP  # noqa: E402
from nb1a_guard import OpenGuard  # noqa: E402  (accepted allowlist file-open guard, read-only)

PREFIX = "[nb1c]"
FROZEN = ["../source/rgb-source-manifest.json", "attention-score.npz", "attention-diagnostics.npz",
          "candidate-gazes.json", "nms-rounds.json", "selection-summary.json", "selection-opened-files.json"]
SELECTION_CODE = {"nb1c_spec.py": HERE / "nb1c_spec.py", "nb1c_attention.py": HERE / "nb1c_attention.py",
                  "nb1a_spec.py": HERE / "nb1a_spec.py", "nb1a_guard.py": HERE / "nb1a_guard.py",
                  "fsg_geometry.py": SP.SENSOR_SOURCE}
SELECTION_ROUTINES = ("select", "verify_rgb_source", "verify_sensor", "write_selection")   # audited statically

# ---- evaluation-only inputs (contract section 15); opened only after the freeze verifies
NB1A_RUN = SP.SHARED / "previews/natural-bootstrap-1a-range-connectivity"
NB1B_RUN = SP.SHARED / "previews/natural-bootstrap-1b-foveal-serviceability"
EVALUATION_INPUTS = {
    "nb1a/input/range-sensory.npz": (NB1A_RUN / "input/range-sensory.npz",
                                     "02bdf22472ab542545102ec5c3c7f092953a1f89ee2f61ebe62225545ed0883b"),
    "nb1a/discovery/hypothesis-raster.npz": (NB1A_RUN / "discovery/hypothesis-raster.npz",
                                             "513a15e0077fc1f5d84847ff020386687ce7ec28477b71ddc349378fb00bae88"),
    "nb1a/discovery/hypotheses.json": (NB1A_RUN / "discovery/hypotheses.json",
                                       "eecf180faecd7765e15c162b76ae1427dc12212026f439d608f21b9c4357009b"),
    "nb1a/evaluation/reference-cells.npz": (NB1A_RUN / "evaluation/reference-cells.npz",
                                            "54a58d28eab4ade81c7e945fefb379ce6d13f5a149797324bdbb23f1f84f9f76"),
    "nb1a/evaluation/overlap-summary.json": (NB1A_RUN / "evaluation/overlap-summary.json",
                                             "1ad980a4a84af7e0e63b6f81360c85c77e3863d7baa324bf45bcdedfe65691cb"),
    "nb1b/selection/serviceability.json": (NB1B_RUN / "selection/serviceability.json",
                                           "2c83d76cd4c61bea3218b24893effe6e83a2965c9aabd300da7843150e53c1b1"),
    "nb1b/selection/primary-look-queue.json": (NB1B_RUN / "selection/primary-look-queue.json",
                                               "1cc867b1a3fb69ed6be6487625b42ae8912f61536ae2e15bb7986a126795dc10"),
    "nb1b/selection/secondary-look-queue.json": (NB1B_RUN / "selection/secondary-look-queue.json",
                                                 "5481497c62f9c0f154fc2d9eb774103e70e1dd61d8ceb5c84181522e7b9b5875"),
    "nb1b/selection/environment-candidate.json": (NB1B_RUN / "selection/environment-candidate.json",
                                                  "427346e91483fd74caf0afefe518fd2700a3c9cfe5ab27a93aae104dbea59759"),
    "nb1b/selection/serviceability-freeze.json": (NB1B_RUN / "selection/serviceability-freeze.json",
                                                  "f99b7cae02498feb21ae1d80978b57c877c44984067d55c7fd2bbe189efb6e9a"),
}
GAZE_CLASSES = ["GAZE_FULL_SAFE", "GAZE_CENTER_ONLY_SAFE", "GAZE_UNSAFE", "GAZE_NO_RANGE"]
NB1B_CLASSES = ["ENVIRONMENT_CANDIDATE", "PRIMARY_LOOK", "SECONDARY_LOOK", "MARGINAL", "EDGE_ONLY"]
O0_NAME = "O_0 (index 0, noncatalog geometry)"


# ------------------------------------------------------------------ utilities
def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, data) -> None:
    Path(path).write_text(json.dumps(data, indent=1, sort_keys=True, allow_nan=False) + "\n")


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


def log_process(run: Path, command: str, t0: float, status: str) -> None:
    run.mkdir(parents=True, exist_ok=True)
    entry = {"command": command, "argv": sys.argv, "executable": sys.executable, "code": code_state(),
             "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
             "seconds": round(time.time() - t0, 3), "status": status}
    with open(run / "process-log.jsonl", "a") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")


def config_sha256() -> str:
    return hashlib.sha256(json.dumps(SP.SELECTION_CONFIG, sort_keys=True).encode()).hexdigest()


def grid_identity() -> dict:
    d = np.ascontiguousarray(SP.cell_directions_h(), np.float64)
    w = np.ascontiguousarray(SP.row_weights(), np.float64)
    return {"directions_sha256": hashlib.sha256(d.tobytes()).hexdigest(),
            "row_weights_sha256": hashlib.sha256(w.tobytes()).hexdigest(),
            "convention": "yaw = -180 + 0.5 (col + 0.5), pitch = 90 - 0.5 (row + 0.5); "
                          "d = (sin yaw cos pitch, sin pitch, -cos yaw cos pitch)", "width": SP.WIDTH, "height": SP.HEIGHT}


# ------------------------------------------------------------------ path 1: pure RGB selection (sections 2-14)
def verify_rgb_source(path: Path) -> np.ndarray:
    h = sha256(path)
    if h != SP.RGB_SHA256:
        raise SystemExit(f"{PREFIX} STOP RGB source hash mismatch: {h}")
    with np.load(path) as z:
        names = tuple(z.files)
        srgb8 = np.asarray(z["srgb8"]) if "srgb8" in names else None
    if names != SP.RGB_ARRAYS or srgb8 is None or srgb8.dtype != np.uint8 or srgb8.shape != (SP.HEIGHT, SP.WIDTH, 3):
        raise SystemExit(f"{PREFIX} STOP the input is not RGB only at 720 x 360: {names}")
    return srgb8


def verify_sensor() -> str:
    h = sha256(SP.SENSOR_SOURCE)
    if h != SP.SENSOR_SOURCE_SHA256 or SP.CORE_FOV_DEG != 12.0:
        raise SystemExit(f"{PREFIX} STOP accepted sensor source changed: sha256 {h}, CORE_FOV_DEG {SP.CORE_FOV_DEG}")
    return h


def write_selection(out: Path, res: dict) -> None:
    st, pat = res["stats"], res["pattern"]
    np.savez_compressed(out / "attention-score.npz", A=st["A"])
    np.savez_compressed(out / "attention-diagnostics.npz", n_C=st["n_C"], n_S=st["n_S"], W_C=st["W_C"], W_S=st["W_S"],
                        mu_C=st["mu_C"], mu_S=st["mu_S"], V_C=st["V_C"], V_S=st["V_S"], D_RGB=st["D_RGB"],
                        k_center=pat["k_center"], k_disk=pat["k_disk"], reference_column=np.int64(pat["reference_column"]),
                        lut=res["lut"], shift=st["shift"], row_weights=res["weights"])
    write_json(out / "candidate-gazes.json", {
        "schema": "NB1c-candidate-gazes-v1", "truth": SP.TRUTH_DERIVED, "config": SP.SELECTION_CONFIG,
        "params_used": res["params"],
        "statement": "six RGB candidate gaze directions in selection order; derived from the coarse RGB proxy only; "
                     "an attention budget, not an object count; NOT executed",
        "K": len(res["picks"]), "gazes": AT.gaze_records(res)})
    write_json(out / "nms-rounds.json", {
        "schema": "NB1c-nms-rounds-v1", "truth": SP.TRUTH_DERIVED, "rule": SP.SELECTION_CONFIG["nms"],
        "ties": SP.SELECTION_CONFIG["ties"], "d_min_rad": res["params"]["d_min"],
        "newly_suppressed": "previously eligible cells with alpha + ANGLE_EPS_RAD < D_MIN, the selected cell included",
        "margin_to_next_eligible": "selected score minus the best eligible score outside the tie set (diagnostic)",
        "rounds": res["rounds"]})


def select(run: Path) -> dict:
    src, out = run / "source", run / "selection"
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"{PREFIX} STOP {out} exists: the canonical RGB selection is made once")
    src.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    code = code_state()
    t0 = time.perf_counter()
    with OpenGuard("selection", [SP.RGB_SOURCE], [src, out]) as g:
        srgb8 = verify_rgb_source(SP.RGB_SOURCE)
        sensor_sha = verify_sensor()
        write_json(src / "rgb-source-manifest.json", {
            "schema": "NB1c-rgb-source-manifest-v1", "truth": SP.TRUTH_ORACLE,
            "statement": "the accepted coarse spherical RGB proxy (controlled sensory proxy from Blender); the only "
                         "scene data selection reads; read-only; never regenerated",
            "rgb_source": {"path": str(SP.RGB_SOURCE), "sha256": SP.RGB_SHA256, "verified": True,
                           "arrays": list(SP.RGB_ARRAYS), "dtype": "uint8", "shape": [SP.HEIGHT, SP.WIDTH, 3]},
            "sensor": {"path": str(SP.SENSOR_SOURCE), "sha256": sensor_sha, "git_blob": SP.SENSOR_SOURCE_BLOB,
                       "CORE_FOV_DEG": SP.CORE_FOV_DEG},
            "grid": grid_identity(), "code": code})
        try:
            res = AT.run(srgb8)
        except AT.DecompositionError as exc:
            raise SystemExit(f"{PREFIX} STOP numerical decomposition: {exc}")
        except AT.BudgetError as exc:
            raise SystemExit(f"{PREFIX} HARD FAIL attention budget: {exc}")
        write_selection(out, res)
        summ = AT.summary(res)
        summ["seconds"] = round(time.perf_counter() - t0, 2)
        write_json(out / "selection-summary.json", summ)
    rec = g.record()
    rec["truth_firewall_violations"] = len(rec["violations"])
    write_json(out / "selection-opened-files.json", rec)
    if rec["violations"]:
        raise SystemExit(f"{PREFIX} STOP selection truth-firewall violations: {rec['violations']}")
    sel = ", ".join(f"g{x['rank']} ({x['yaw_deg']:+.2f}, {x['pitch_deg']:+.2f}) A={x['A']:.4g}" for x in summ["selected"])
    print(f"{PREFIX} select: {summ['candidate_directions']} candidates; {sel}; min pair {summ['min_pairwise_deg']:.3f} deg; "
          f"guard data reads {len(rec['data_reads'])}, violations 0 ({summ['seconds']} s)")
    return summ


def freeze(run: Path) -> dict:
    sel = run / "selection"
    rec = {"schema": "NB1c-rgb-gaze-freeze-v1", "truth": SP.TRUTH_DERIVED,
           "statement": "the pure RGB attention result, frozen before any depth / range / hypothesis / reference "
                        "information is opened",
           "files": {n: sha256(sel / n) for n in FROZEN},
           "rgb_source": {"path": str(SP.RGB_SOURCE), "sha256": sha256(SP.RGB_SOURCE)},
           "sensor_constants": SP.SENSOR_CONSTANTS,
           "sensor_source": {"path": str(SP.SENSOR_SOURCE), "sha256": sha256(SP.SENSOR_SOURCE)},
           "selection_config": SP.SELECTION_CONFIG, "selection_config_sha256": config_sha256(),
           "selection_code": {n: sha256(p) for n, p in SELECTION_CODE.items()}, "grid": grid_identity(),
           "gazes": [{k: g[k] for k in ("rank", "row", "col")} for g in read_json(sel / "candidate-gazes.json")["gazes"]],
           "code": code_state(), "frozen_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    write_json(sel / "rgb-gaze-freeze.json", rec)
    print(f"{PREFIX} freeze: {len(rec['files'])} selection products hashed")
    return rec


def verify_freeze(run: Path) -> dict:
    sel = run / "selection"
    fz = read_json(sel / "rgb-gaze-freeze.json")
    bad = [n for n, h in fz["files"].items() if sha256(sel / n) != h]
    if bad or set(fz["files"]) != set(FROZEN):
        raise SystemExit(f"{PREFIX} STOP frozen RGB gaze products do not verify: {bad}")
    return fz


# ------------------------------------------------------------------ path 2: reference / evaluation (section 15)
def footprint_at(alpha: np.ndarray, labels_flat: np.ndarray, own: int, radius: float) -> dict:
    """NB1b's footprint rule at the RGB gaze: alpha <= R + eps over the full sphere; SAFE iff every cell is ``own``."""
    cells = np.flatnonzero(alpha <= radius + SP.ANGLE_EPS_RAD)
    lab = labels_flat[cells]
    inv = int((lab == 0).sum())
    own_n = int((lab == own).sum()) if own > 0 else 0
    other = int(len(cells)) - own_n - inv
    return {"total_cells": int(len(cells)), "own_cells": own_n, "other_cells": other,
            "other_hypotheses": len(set(lab[(lab != own) & (lab != 0)].tolist())), "invalid_cells": inv,
            "containment_fraction": own_n / len(cells), "safe": bool(own > 0 and own_n == len(cells))}


def gaze_class(own: int, center: dict, full: dict) -> str:
    if own == 0:
        return "GAZE_NO_RANGE"
    if full["safe"]:
        return "GAZE_FULL_SAFE"
    return "GAZE_CENTER_ONLY_SAFE" if center["safe"] else "GAZE_UNSAFE"


def reference_at(cells: np.ndarray, valid: np.ndarray, oid: np.ndarray, o0: np.ndarray, names: dict) -> dict:
    v, o, z = valid[cells], oid[cells], o0[cells]
    ids, cnt = np.unique(o[v & ~z], return_counts=True)
    top = sorted(zip(cnt.tolist(), ids.tolist()), key=lambda x: (-x[0], x[1]))[:4]
    return {"cells": int(len(cells)), "no_geometry_cells": int((~v).sum()), "O0_cells": int((v & z).sum()),
            "catalog_cells": int((v & ~z).sum()),
            "top_authored": [{"o": int(i), "name": names.get(int(i), ""), "cells": int(c)} for c, i in top]}


def cell_reference(flat: int, valid, oid, o0, names) -> dict:
    if not valid[flat]:
        return {"kind": "no geometry", "o": None, "name": None}
    if o0[flat]:
        return {"kind": "O_0", "o": 0, "name": O0_NAME}
    return {"kind": "authored", "o": int(oid[flat]), "name": names.get(int(oid[flat]), "")}


def score_rank(a_flat: np.ndarray, idx: int) -> int:
    """1-based rank in the full raster ordered by A desc, then row, then column (row-major index)."""
    v = a_flat[idx]
    return int((a_flat > v).sum() + (a_flat[:idx] == v).sum() + 1)


def evaluation_summary(gazes: list[dict], A: np.ndarray, data: dict, fz: dict) -> tuple[dict, dict]:
    dirs = SP.cell_directions_h().reshape(-1, 3)
    labels = data["labels"].reshape(-1).astype(np.int64)
    valid = data["valid"].reshape(-1)
    rng = data["range_m"].reshape(-1)
    oid, o0 = data["object_index"].reshape(-1).astype(np.int64), data["o0_mask"].reshape(-1)
    names = data["names"]
    hyp_by_label = {h["label"]: h for h in data["hypotheses"]}
    cls_by_id = {r["id"]: r["class"] for r in data["serviceability"]}
    seeds = [(f"P{e['rank']}", e) for e in data["primary"]] + [(f"S{e['rank']}", e) for e in data["secondary"]]
    seed_dirs = np.array([dirs[e["seed"]["row"] * SP.WIDTH + e["seed"]["col"]] for _t, e in seeds]).reshape(-1, 3)
    out = []
    for g in gazes:
        flat = g["row"] * SP.WIDTH + g["col"]
        d_g = dirs[flat]
        alpha = AT.angular_distance(d_g, dirs)
        own = int(labels[flat])
        cen = footprint_at(alpha, labels, own, SP.R_CENTER_RAD)
        ful = footprint_at(alpha, labels, own, SP.R_FULL_RAD)
        h = hyp_by_label.get(own)
        hid = h["id"] if h else None
        to_seed = AT.angular_distance(d_g, seed_dirs) if len(seeds) else np.zeros(0)
        k = int(np.argmin(to_seed)) if len(seeds) else None
        r = float(rng[flat]) if valid[flat] else None
        out.append({
            "rank": g["rank"], "row": g["row"], "col": g["col"], "yaw_deg": g["yaw_deg"], "pitch_deg": g["pitch_deg"],
            "valid_range": bool(valid[flat]), "range_m": r,
            "point_h_m": [float(x) for x in (r * d_g)] if r is not None else None,
            "nb1a_hypothesis": hid, "nb1a_label": own if own > 0 else None,
            "nb1a_hypothesis_support_sr": h["support_sr"] if h else None,
            "nb1b_class": cls_by_id.get(hid) if hid else None,
            "center": cen, "full": ful, "gaze_class": gaze_class(own, cen, ful),
            "reference_at_gaze": cell_reference(flat, valid, oid, o0, names),
            "center_reference": reference_at(np.flatnonzero(alpha <= SP.R_CENTER_RAD + SP.ANGLE_EPS_RAD), valid, oid, o0,
                                             names),
            "nearest_nb1b_seed": ({"seed": seeds[k][0], "id": seeds[k][1]["id"],
                                   "angular_distance_deg": float(np.degrees(to_seed[k]))} if k is not None else None)})
    hits = [e["nb1a_hypothesis"] for e in out if e["nb1a_hypothesis"]]
    dup = {hid: [e["rank"] for e in out if e["nb1a_hypothesis"] == hid] for hid in sorted(set(hits)) if hits.count(hid) > 1}
    pts = {e["rank"]: np.array(e["point_h_m"]) for e in out if e["point_h_m"] is not None}
    sep = [[(float(np.linalg.norm(pts[a] - pts[b])) if a in pts and b in pts else None) for b in range(1, len(out) + 1)]
           for a in range(1, len(out) + 1)]
    agg = {"gazes": len(out), "valid_range": sum(e["valid_range"] for e in out),
           "no_valid_range": sum(not e["valid_range"] for e in out),
           "distinct_nb1a_hypotheses": len(set(hits)),
           "duplicate_gazes_into_same_hypothesis": len(hits) - len(set(hits)), "duplicates": dup,
           "nb1b_class_hits": {c: sum(e["nb1b_class"] == c for e in out) for c in NB1B_CLASSES},
           "gaze_class_counts": {c: sum(e["gaze_class"] == c for e in out) for c in GAZE_CLASSES}}
    a_flat = A.reshape(-1)
    gdirs = np.array([dirs[g["row"] * SP.WIDTH + g["col"]] for g in gazes])
    comp = []
    for tag, e in seeds:
        flat = e["seed"]["row"] * SP.WIDTH + e["seed"]["col"]
        dd = AT.angular_distance(dirs[flat], gdirs)
        k = int(np.argmin(dd))
        comp.append({"seed": tag, "id": e["id"], "row": e["seed"]["row"], "col": e["seed"]["col"],
                     "yaw_deg": e["seed"]["yaw_deg"], "pitch_deg": e["seed"]["pitch_deg"], "A": float(a_flat[flat]),
                     "rank_in_full_raster": score_rank(a_flat, flat), "candidates": int(a_flat.size),
                     "nearest_gaze": gazes[k]["rank"], "nearest_gaze_deg": float(np.degrees(dd[k])),
                     "within_D_MIN_of_a_gaze": bool((dd + SP.ANGLE_EPS_RAD < SP.D_MIN_RAD).any()),
                     "within_R_FULL_of_a_gaze": bool((dd <= SP.R_FULL_RAD + SP.ANGLE_EPS_RAD).any())})
    common = {"computed_after_freeze": True, "frozen_selection_sha256": fz["files"],
              "reference_inputs_sha256": {n: h for n, (_p, h) in EVALUATION_INPUTS.items()}}
    ev = {"schema": "NB1c-candidate-evaluation-v1", "truth": SP.TRUTH_REFERENCE,
          "statement": "POST-FREEZE REFERENCE / EVALUATION: descriptive relation of the frozen RGB gazes to range, NB1a "
                       "hypotheses, NB1b classes and authored / O_0 reference; no target; not ground truth; no "
                       "accuracy / precision / recall / IoU; changes no gaze and no order; no gaze was executed",
          "footprint_rule": "NB1b: alpha <= R + ANGLE_EPS_RAD over the full sphere at the RGB gaze itself; SAFE iff every "
                            "cell belongs to the gaze cell's NB1a hypothesis; no geometry counts as outside",
          "gaze_classes": GAZE_CLASSES, "gazes": out, "aggregate": agg,
          "pairwise_3d_separation_m": sep, **common}
    nb = {"schema": "NB1c-nb1b-comparison-v1", "truth": SP.TRUTH_REFERENCE,
          "statement": "descriptive: the accepted NB1b queued seeds in the frozen RGB attention raster; no gaze moved",
          "rank_order": "A desc, then row, then column; 1-based over all 259,200 candidates", "seeds": comp, **common}
    return ev, nb


def load_evaluation_inputs() -> dict:
    p = {n: path for n, (path, _h) in EVALUATION_INPUTS.items()}
    with np.load(p["nb1a/input/range-sensory.npz"]) as z:
        range_m, valid = np.asarray(z["range_m"]), np.asarray(z["valid_mask"])
    with np.load(p["nb1a/discovery/hypothesis-raster.npz"]) as z:
        labels = np.asarray(z["labels"])
    with np.load(p["nb1a/evaluation/reference-cells.npz"]) as z:
        oid, o0 = np.asarray(z["object_index"]), np.asarray(z["o0_mask"])
    ov = read_json(p["nb1a/evaluation/overlap-summary.json"])
    return {"range_m": range_m, "valid": valid, "labels": labels, "object_index": oid, "o0_mask": o0,
            "names": {int(r["o"]): r["name"] for r in ov["per_reference_id"] if int(r["o"]) > 0},
            "hypotheses": read_json(p["nb1a/discovery/hypotheses.json"])["hypotheses"],
            "serviceability": read_json(p["nb1b/selection/serviceability.json"])["hypotheses"],
            "primary": read_json(p["nb1b/selection/primary-look-queue.json"])["queue"],
            "secondary": read_json(p["nb1b/selection/secondary-look-queue.json"])["queue"],
            "environment": read_json(p["nb1b/selection/environment-candidate.json"])["candidates"],
            "nb1b_freeze": read_json(p["nb1b/selection/serviceability-freeze.json"])}


def evaluate(run: Path) -> dict:
    sel, out = run / "selection", run / "evaluation"
    out.mkdir(parents=True, exist_ok=True)
    frozen = [sel / n for n in FROZEN] + [sel / "rgb-gaze-freeze.json"]
    refs = [path for path, _h in EVALUATION_INPUTS.values()]
    with OpenGuard("evaluation", frozen + refs, [out]) as g:
        fz = verify_freeze(run)
        g.mark("freeze_verified")
        gazes = read_json(sel / "candidate-gazes.json")["gazes"]
        with np.load(sel / "attention-score.npz") as z:
            A = np.asarray(z["A"])
        g.mark("reference_access_begins")
        bad = [n for n, (path, h) in EVALUATION_INPUTS.items() if sha256(path) != h]
        if bad:
            raise SystemExit(f"{PREFIX} STOP evaluation input hash mismatch: {bad}")
        data = load_evaluation_inputs()
        ev, nb = evaluation_summary(gazes, A, data, fz)
        write_json(out / "candidate-evaluation.json", ev)
        write_json(out / "nb1b-comparison.json", nb)
    rec = g.record()
    rec["ordered_data_events"] = [e.get("label") or e.get("path") for e in rec["events"]
                                  if e.get("event") == "mark" or e.get("kind") == "data-read"]
    write_json(out / "evaluation-opened-files.json", rec)
    after = verify_freeze(run)
    if rec["violations"]:
        raise SystemExit(f"{PREFIX} STOP evaluation guard violations: {rec['violations']}")
    a = ev["aggregate"]
    print(f"{PREFIX} evaluate: valid range {a['valid_range']}/{a['gazes']}; distinct NB1a hypotheses "
          f"{a['distinct_nb1a_hypotheses']}; NB1b classes {a['nb1b_class_hits']}; gaze classes {a['gaze_class_counts']}; "
          f"frozen products re-verified ({len(after['files'])})")
    return ev


# ------------------------------------------------------------------ synthetic known answers (section 19)
def _paint_disk(img: np.ndarray, row: int, col: int, radius_deg: float, color, pattern=None) -> np.ndarray:
    dirs = SP.cell_directions_h().reshape(-1, 3)
    a = AT.angular_distance(dirs[row * SP.WIDTH + col], dirs).reshape(SP.HEIGHT, SP.WIDTH)
    m = a <= math.radians(radius_deg) + SP.ANGLE_EPS_RAD
    if pattern is None:
        img[m] = color
    else:   # two-colour checkerboard by (row + col) parity
        rr, cc = np.nonzero(m)
        par = (rr + cc) % 2 == 0
        img[rr[par], cc[par]] = pattern[0]
        img[rr[~par], cc[~par]] = pattern[1]
    return img


def _checker_sphere(c1, c2) -> np.ndarray:
    rr, cc = np.mgrid[0:SP.HEIGHT, 0:SP.WIDTH]
    img = np.empty((SP.HEIGHT, SP.WIDTH, 3), np.uint8)
    img[(rr + cc) % 2 == 0] = c1
    img[(rr + cc) % 2 == 1] = c2
    return img


def _blank(color) -> np.ndarray:
    img = np.empty((SP.HEIGHT, SP.WIDTH, 3), np.uint8)
    img[:] = color
    return img


def direct_stats(srgb8: np.ndarray, row: int, col: int) -> dict:
    """The contract's definitions evaluated directly at one candidate (atan2 membership, two-pass variance)."""
    lut = SP.linear_table()
    x = lut[srgb8].reshape(-1, 3)
    w = np.repeat(SP.row_weights(), SP.WIDTH)
    dirs = SP.cell_directions_h().reshape(-1, 3)
    a = AT.angular_distance(dirs[row * SP.WIDTH + col], dirs)
    out = {}
    for r, m in (("C", a <= SP.R_CENTER_RAD + SP.ANGLE_EPS_RAD),
                 ("S", (a > SP.R_CENTER_RAD + SP.ANGLE_EPS_RAD) & (a <= SP.R_SURROUND_RAD + SP.ANGLE_EPS_RAD))):
        Wr = float(w[m].sum())
        mu = (w[m, None] * x[m]).sum(0) / Wr
        out[r] = {"n": int(m.sum()), "W": Wr, "mu": mu, "V": float((w[m] * ((x[m] - mu) ** 2).sum(1)).sum() / Wr),
                  "cells": np.flatnonzero(m)}
    D = float(np.linalg.norm(out["C"]["mu"] - out["S"]["mu"]))
    out["D"] = D
    out["A"] = D / math.sqrt(out["C"]["V"] + out["S"]["V"] + SP.VAR_EPS)
    return out


def _unit(v) -> np.ndarray:
    v = np.asarray(v, np.float64)
    return v / np.linalg.norm(v)


def _rotate(v, axis, ang) -> np.ndarray:
    """Rodrigues rotation of unit vector ``v`` about unit ``axis`` by ``ang``."""
    v, k = _unit(v), _unit(axis)
    return v * math.cos(ang) + np.cross(k, v) * math.sin(ang) + k * (k @ v) * (1 - math.cos(ang))


def synthetic_cases() -> list[tuple]:
    """(name, function(variant) -> (ok, detail)).  ``variant``: AT.run / select_gazes mutation keywords."""
    H, W = SP.HEIGHT, SP.WIDTH
    dirs = SP.cell_directions_h().reshape(-1, 3)

    def run(img, v):
        return AT.run(img, **v)

    def nms(scores, v, cand_dirs=None):
        dmin = v.get("d_min") if v.get("d_min") is not None else 2.0 * v.get("r_full", SP.R_FULL_RAD)
        return AT.select_gazes(scores, dirs if cand_dirs is None else cand_dirs, v.get("k_budget", SP.K), dmin,
                               tie_break=v.get("tie_break", True))[0]

    cases = []

    def uniform(v):
        res = run(_blank((77, 120, 200)), v)
        a = res["stats"]["A"]
        elig, want = np.ones(H * W, bool), []
        for _ in range(SP.K):
            g = int(np.flatnonzero(elig)[0])
            want.append(g)
            elig &= ~(AT.angular_distance(dirs[g], dirs) + SP.ANGLE_EPS_RAD < SP.D_MIN_RAD)
        ok = bool((a == 0).all()) and res["picks"] == want and want[0] == 0
        return ok, {"max_abs_A": float(np.abs(a).max()), "picks": res["picks"], "expected": want}
    cases.append(("uniform sphere: A = 0 exactly; tie-broken NMS returns six gazes from (0, 0)", uniform))

    red, bg = (200, 40, 40), (60, 90, 70)

    def coherent(v):
        res = run(_paint_disk(_blank(bg), 180, 360, 6.0, red), v)
        a = res["stats"]["A"]
        g0 = 180 * W + 360
        second = np.partition(a.reshape(-1), -2)[-2]
        ok = res["picks"][0] == g0 and a[180, 360] >= 1e5 and a[180, 360] > 1e3 * second
        return ok, {"A_centre": float(a[180, 360]), "second_best": float(second), "first_pick": res["picks"][0]}
    cases.append(("coherent coloured centre -> unique maximum (A >= 1e5) and first gaze", coherent))
    lut = SP.linear_table()
    c1, c2 = (240, 20, 60), (150, 60, 20)
    mix_lin = (lut[list(c1)] + lut[list(c2)]) / 2
    mix = tuple(int(np.argmin(np.abs(lut - m))) for m in mix_lin)

    def hetero_centre(v):
        a = run(_paint_disk(_blank(bg), 180, 360, 6.0, mix), v)["stats"]
        b = run(_paint_disk(_blank(bg), 180, 360, 6.0, None, pattern=(c1, c2)), v)["stats"]
        ok = (b["V_C"][180, 360] > a["V_C"][180, 360] + 1e-3 and b["A"][180, 360] < a["A"][180, 360]
              and abs(b["D_RGB"][180, 360] - a["D_RGB"][180, 360]) <= 0.05 * a["D_RGB"][180, 360])
        return ok, {"coherent": {k: float(a[k][180, 360]) for k in ("A", "D_RGB", "V_C")},
                    "heterogeneous": {k: float(b[k][180, 360]) for k in ("A", "D_RGB", "V_C")}, "mix_colour": mix}
    cases.append(("heterogeneous centre with the same mean contrast -> larger V_C, lower A", hetero_centre))
    b1, b2 = (30, 120, 60), (95, 60, 85)

    def hetero_surround(v):
        a = run(_paint_disk(_blank(bg), 180, 360, 6.0, red), v)["stats"]
        b = run(_paint_disk(_checker_sphere(b1, b2), 180, 360, 6.0, red), v)["stats"]
        ok = b["V_S"][180, 360] > a["V_S"][180, 360] + 1e-3 and b["A"][180, 360] < a["A"][180, 360]
        return ok, {"coherent": {k: float(a[k][180, 360]) for k in ("A", "V_S")},
                    "heterogeneous": {k: float(b[k][180, 360]) for k in ("A", "V_S")}}
    cases.append(("heterogeneous surround -> larger V_S, lower A", hetero_surround))
    known = {0: 0.0, 10: 0.003035269835488375, 11: 0.003346535763899161, 128: 0.21586050011389926, 255: 1.0}

    def srgb(v):
        t = SP.linear_table(v.get("linear", True))
        got = {k: float(t[k]) for k in known}
        return got == known and t[10] == 10 / 255 / 12.92, {"got": got, "expected": known}
    cases.append(("known sRGB -> linear values (0, 10, 11, 128, 255; both branches)", srgb))
    feats = [(150, 100, (230, 30, 30)), (190, 200, (30, 200, 40)), (120, 330, (40, 40, 220)),
             (200, 450, (240, 220, 30)), (160, 560, (200, 40, 200)), (90, 640, (30, 210, 210))]

    def seam(v):
        img = _blank(bg)
        for r, c, col in feats:
            img = _paint_disk(img, r, c, 6.0, col)
        s = W - 100   # the first feature (column 100) moves onto the seam (column 0)
        a = run(img, v)
        b = run(np.roll(img, s, axis=1), v)
        same = np.array_equal(np.roll(a["stats"]["A"], s, axis=1), b["stats"]["A"])
        mapped = [(p // W) * W + (p % W + s) % W for p in a["picks"]]
        pos = all(a["stats"]["A"].reshape(-1)[p] > 0 for p in a["picks"])
        on_seam = any(p % W == 0 for p in b["picks"])
        ok = same and pos and on_seam and mapped == b["picks"]
        return bool(ok), {"raster_roll_equal": bool(same), "picks_interior": a["picks"], "picks_seam": b["picks"],
                          "mapped": mapped, "a_pick_on_the_seam": on_seam}
    cases.append(("feature translated across the longitude seam -> exact raster roll, corresponding picks", seam))

    def pole(v):
        img = _blank(bg)
        img[0:8] = red     # a polar cap
        res = run(img, v)
        kc = res["pattern"]["k_center"]
        full_rows = all(int(kc[0, j]) >= W // 2 for j in range(12))
        d = direct_stats(img, 0, 123)
        mine = np.sort(np.concatenate([(j * W + (123 + np.arange(-k, k + 1)) % W) if k < W // 2 else j * W + np.arange(W)
                                       for j, k in enumerate(kc[0].tolist()) if k >= 0]))
        same_set = np.array_equal(mine, d["C"]["cells"])
        row0 = res["stats"]["A"][0]
        ok = full_rows and same_set and bool((row0 == row0[0]).all()) and int(res["stats"]["n_C"][0, 123]) == d["C"]["n"]
        return ok, {"rows_0_11_full": full_rows, "center_set_equals_direct": bool(same_set),
                    "n_C_row0": int(res["stats"]["n_C"][0, 123]), "row0_constant": bool((row0 == row0[0]).all())}
    cases.append(("near-pole candidate: CENTER holds rows 0-11 entirely; equals the direct cell set", pole))

    def weighting(v):
        img = _blank(bg)
        r0, c0 = 60, 360
        img = _paint_disk(img, r0, c0, 6.0, (255, 0, 0))
        up = img[:r0 + 1].copy()
        img = _paint_disk(img, r0, c0, 6.0, (0, 0, 255))
        img[:r0 + 1] = up
        res = run(img, v)
        d = direct_stats(img, r0, c0)
        x = SP.linear_table()[img].reshape(-1, 3)
        raw = x[d["C"]["cells"]].mean(0)
        got = res["stats"]["mu_C"][r0, c0]
        ok = float(np.abs(got - d["C"]["mu"]).max()) <= 1e-12 and float(np.abs(d["C"]["mu"] - raw).max()) > 1e-3
        return ok, {"mu_C": got.tolist(), "weighted_direct": d["C"]["mu"].tolist(), "raw_count_mean": raw.tolist()}
    cases.append(("solid-angle weighting: latitude-split centre at pitch ~60 deg -> weighted, not raw, mean", weighting))

    def ties(v):
        a = np.zeros((H, W))
        a[130, 400] = a[130, 20] = 7.0
        a[140, 0] = 7.0 - 1e-6
        p1 = nms(a, v)[0]
        b = np.zeros((H, W))
        b[120, 10] = 5.0
        b[100, 600] = 5.0 - 4e-12      # inside the tie window 5e-12
        b[90, 300] = 5.0 - 6e-12       # outside
        p2 = nms(b, v)[0]
        ok = p1 == 130 * W + 20 and p2 == 100 * W + 600
        return ok, {"exact_tie_pick": [p1 // W, p1 % W], "near_tie_pick": [p2 // W, p2 % W]}
    cases.append(("exact and near score ties -> smaller row, then column; outside the window excluded", ties))
    g0 = 180 * W + 360
    al = AT.angular_distance(dirs[g0], dirs)
    q_idx = 155 * W + 383                      # 16.927 deg (north-east): beyond D_MIN, inside 2 sqrt(2) 6 deg
    p2_idx = 180 * W + 393                     # about 16.5 deg (east): inside D_MIN
    p3_idx = 180 * W + 300                     # about 30 deg (west)

    def nms_case(v):
        a = np.zeros((H, W))
        a.reshape(-1)[[g0, p2_idx, q_idx, p3_idx]] = [10.0, 9.5, 9.0, 8.0]
        picks = nms(a, v)
        geom = SP.D_MIN_RAD < al[q_idx] < math.radians(2 * math.sqrt(2) * 6.0) and al[p2_idx] < SP.D_MIN_RAD
        ok = geom and picks[:3] == [g0, q_idx, p3_idx] and p2_idx not in picks
        return ok, {"picks_first3": picks[:3], "expected": [g0, q_idx, p3_idx], "suppressed_peak": p2_idx,
                    "q_deg": float(np.degrees(al[q_idx])), "p2_deg": float(np.degrees(al[p2_idx]))}
    cases.append(("NMS: a peak inside D_MIN is suppressed; peaks just beyond D_MIN and at 30 deg remain", nms_case))

    def boundary(v):
        g = _unit([0.0, 0.0, -1.0])
        q = _rotate(g, [0, 1, 0], SP.D_MIN_RAD)                 # exactly at D_MIN
        r = _rotate(g, [0, 1, 0], -(SP.D_MIN_RAD - 1e-9))       # inside by 1e-9 rad
        s = _rotate(g, [1, 0, 0], SP.D_MIN_RAD - 5e-13)         # inside by less than ANGLE_EPS_RAD
        far = [_rotate(g, [1, 0, 0], -math.radians(t)) for t in (60.0, 100.0, 140.0)]
        cand = np.array([g, r, q, s] + far)
        sc = np.array([10.0, 9.0, 8.0, 7.5, 7.0, 6.0, 5.0])
        dmin = v.get("d_min") if v.get("d_min") is not None else 2.0 * v.get("r_full", SP.R_FULL_RAD)
        picks = AT.select_gazes(sc, cand, 6, dmin, tie_break=v.get("tie_break", True))[0]
        return picks == [0, 2, 3, 4, 5, 6], {"picks": picks, "expected": [0, 2, 3, 4, 5, 6],
                                             "alpha_q_minus_D_MIN": float(AT.angular_distance(g, q[None])[0] - SP.D_MIN_RAD)}
    cases.append(("exact D_MIN boundary: at D_MIN eligible; D_MIN - 1e-9 suppressed; within eps eligible", boundary))

    def direct(v):
        rng = np.random.default_rng(20261003)
        img = rng.integers(0, 256, (H, W, 3), dtype=np.uint8)
        img = _paint_disk(img, 30, 700, 9.0, (250, 250, 250))
        res = run(img, v)
        st = res["stats"]
        worst, bad = 0.0, []
        for r, c in ((0, 0), (0, 359), (3, 719), (11, 5), (12, 400), (60, 10), (180, 0), (180, 719), (181, 360),
                     (300, 250), (348, 700), (359, 359)):
            d = direct_stats(img, r, c)
            if (int(st["n_C"][r, c]), int(st["n_S"][r, c])) != (d["C"]["n"], d["S"]["n"]):
                bad.append((r, c))
            worst = max(worst, float(np.abs(st["mu_C"][r, c] - d["C"]["mu"]).max()),
                        float(np.abs(st["mu_S"][r, c] - d["S"]["mu"]).max()), abs(st["V_C"][r, c] - d["C"]["V"]),
                        abs(st["V_S"][r, c] - d["S"]["V"]))
            if abs(st["A"][r, c] - d["A"]) > 1e-6 + 1e-9 * abs(d["A"]):
                bad.append((r, c, "A"))
        return not bad and worst <= 1e-11, {"count_or_score_mismatch": bad, "worst_stat_abs_diff": worst}
    cases.append(("decomposition equals the direct definitions at sampled candidates (poles, seam, equator)", direct))

    def budget(v):
        cand = np.array([_unit([1, 0, 0]), _unit([0, 1, 0]), _unit([0, 0, 1])])
        try:
            AT.select_gazes(np.array([3.0, 2.0, 1.0]), cand, v.get("k_budget", SP.K), SP.D_MIN_RAD)
        except AT.BudgetError as exc:
            return True, {"raised": str(exc)}
        return False, {"raised": False}
    cases.append(("an NMS that cannot produce K directions raises (HARD FAIL)", budget))
    return cases


def synthetic_results(**variant) -> list[dict]:
    """Run every known-answer case; ``variant`` (run / NMS keywords) exists only for the mutation suite."""
    out = []
    for name, fn in synthetic_cases():
        try:
            ok, detail = fn(variant)
        except (AT.DecompositionError, AT.BudgetError) as exc:
            ok, detail = False, {"raised": f"{type(exc).__name__}: {exc}"}
        out.append({"name": name, "ok": bool(ok), "detail": detail})
    return out


def _jsonable(x):
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    if isinstance(x, np.ndarray):
        return _jsonable(x.tolist())
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        return float(x)
    return x


def synthetic(run: Path) -> dict:
    out = run / "synthetic"
    out.mkdir(parents=True, exist_ok=True)
    results = synthetic_results()
    for x in results:
        print(f"{PREFIX} synthetic {'PASS' if x['ok'] else 'FAIL'} {x['name']}")
    report = {"schema": "NB1c-synthetic-report-v1", "code": code_state(), "constants": SP.SENSOR_CONSTANTS,
              "cases": _jsonable(results), "passed": all(x["ok"] for x in results),
              "note": "known-answer RGB spheres and score rasters; no Blender, no Classroom"}
    write_json(out / "synthetic-report.json", report)
    print(f"{PREFIX} synthetic {sum(x['ok'] for x in results)}/{len(results)} "
          f"{'NB1C_SYNTHETIC_PASS' if report['passed'] else 'FAILED'}")
    return report


# ------------------------------------------------------------------ manifest
def write_manifest(run: Path) -> dict:
    files = sorted(str(p.relative_to(run)) for p in run.rglob("*") if p.is_file()
                   and p.name not in ("manifest.json", "check-summary.json", "process-log.jsonl"))
    m = {"schema": "NB1c-manifest-v1", "experiment": "Natural Bootstrap-1c: RGB Candidate Gaze",
         "contract": "docs/natural-bootstrap/nb1c-rgb-candidate-gaze-contract.md", "code": code_state(),
         "base_commit": SP.BASE_COMMIT, "rgb_source": {"path": str(SP.RGB_SOURCE), "sha256": SP.RGB_SHA256},
         "evaluation_inputs": {n: {"path": str(p), "sha256": h} for n, (p, h) in EVALUATION_INPUTS.items()},
         "sensor_source": {"path": str(SP.SENSOR_SOURCE), "sha256": SP.SENSOR_SOURCE_SHA256},
         "truth": {"source/": SP.TRUTH_ORACLE, "selection/": SP.TRUTH_DERIVED, "evaluation/": SP.TRUTH_REFERENCE},
         "files": {f: sha256(run / f) for f in files}}
    write_json(run / "manifest.json", m)
    return m


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("synthetic", "select", "freeze", "evaluate", "visualize"):
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
        if a.cmd == "select":
            select(run)
        elif a.cmd == "freeze":
            freeze(run)
        elif a.cmd == "evaluate":
            evaluate(run)
        elif a.cmd == "visualize":
            import nb1c_visuals
            nb1c_visuals.visualize(run, a.visuals.resolve())
            write_manifest(run)
        status = "ok"
        return 0
    finally:
        log_process(run, a.cmd, t0, status)


if __name__ == "__main__":
    raise SystemExit(main())
