"""Breadth-1: Classroom-234 spherical glance (host side: run order, extraction, analysis).

Contract: docs/classroom-oracle/breadth-1-spherical-glance-contract.md.

    .venv/bin/python tools/classroom_oracle/breadth1_glance.py synthetic --run RUN
    .venv/bin/python tools/classroom_oracle/breadth1_glance.py preflight --run RUN
    .venv/bin/python tools/classroom_oracle/breadth1_glance.py render    --run RUN   # exactly once
    .venv/bin/python tools/classroom_oracle/breadth1_glance.py analyze   --run RUN
    .venv/bin/python tools/classroom_oracle/breadth1_glance.py visualize --run RUN --visuals VIS

``synthetic`` renders a factory-startup plumbing scene (no Classroom) through the same camera/pass
configuration and checks orientation, passes, first-hit semantics, the seam and the weights.
``preflight`` loads the Classroom without rendering.  ``render`` makes the single canonical
observation and refuses to run twice.  ``analyze`` and ``visualize`` read only the saved EXR and the
accepted sources.  No controller is imported or executed.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess
import sys
import time

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE.parent))  # tools/: exr_lite (accepted reader)
sys.path.insert(0, str(HERE))

import breadth1_spec as SP  # noqa: E402
from exr_lite import read_uncompressed_exr  # noqa: E402

PREFIX = "[breadth1]"
RENDER_SCRIPT = HERE / "breadth1_render.py"
BLENDER = "blender"
INDEX0_NONCATALOG, INDEX0_NO_GEOMETRY, AUTHORED = 2, 3, 1


# ------------------------------------------------------------------ small utilities
def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=1, sort_keys=True, allow_nan=False) + "\n")


def read_json(path: Path):
    return json.loads(Path(path).read_text())


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()


def code_state() -> dict:
    head = git("rev-parse", "HEAD")
    dirty = bool(git("status", "--porcelain", "--untracked-files=no")
                 or git("status", "--porcelain", "--", "tools", "docs", "fov3d", "scripts"))
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    try:
        upstream = git("rev-parse", f"origin/{branch}")
    except subprocess.CalledProcessError:
        upstream = None
    return {"commit": head, "dirty": dirty, "branch": branch, "pushed": upstream == head}


def source_path(key: str) -> Path:
    return SP.SHARED / SP.SOURCES[key][0]


def verify_sources(keys=("seeds", "catalog", "controller02_result", "blend")) -> dict:
    got = {}
    for k in keys:
        p = source_path(k)
        h = sha256(p)
        if h != SP.SOURCES[k][1]:
            raise SystemExit(f"{PREFIX} STOP source {k} sha256 {h} != accepted {SP.SOURCES[k][1]}")
        got[k] = {"path": str(p), "sha256": h}
    return got


def log_process(run: Path, entry: dict) -> None:
    with open(run / "process-log.jsonl", "a") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")


def blender(run: Path, mode: str, args: list[str], blend: Path | None) -> dict:
    argv = [BLENDER, "-b"] + ([str(blend)] if blend else ["--factory-startup"]) + [
        "--python-exit-code", "1", "-P", str(RENDER_SCRIPT), "--", "--mode", mode] + args
    t0 = time.time()
    started = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    proc = subprocess.run(argv, cwd=REPO, capture_output=True, text=True)
    entry = {"mode": mode, "argv": argv, "started_utc": started, "seconds": round(time.time() - t0, 3),
             "returncode": proc.returncode, "code": code_state()}
    log_process(run, entry)
    return {"entry": entry, "log": proc.stdout + proc.stderr}


# ------------------------------------------------------------------ extraction
def extract_exr(path: Path) -> dict:
    """Aligned Combined RGB, Object Index and Position from one multilayer EXR (row 0 = top)."""
    ch = read_uncompressed_exr(str(path))

    def one(suffix: str) -> np.ndarray:
        keys = [k for k in ch if k.endswith(suffix)]
        if len(keys) != 1:
            raise RuntimeError(f"expected one EXR channel ending {suffix!r}, got {keys}")
        return np.asarray(ch[keys[0]])

    raw = one("Object Index.X").astype(np.float32)
    integral = bool(np.all(raw == np.rint(raw)) and raw.min() >= 0)
    return {"rgb": np.stack([one(f"Combined.{c}") for c in "RGB"], -1).astype(np.float32),
            "instance": np.rint(raw).astype(np.int32),
            "position_w": np.stack([one(f"Position.{c}") for c in "XYZ"], -1).astype(np.float32),
            "index_integral": integral, "channels": sorted(ch)}


def head_points(position_w: np.ndarray, r_wh: np.ndarray, o_w: np.ndarray) -> np.ndarray:
    return (position_w.astype(np.float64) - o_w) @ r_wh


def cell_classes(instance: np.ndarray, position_w: np.ndarray) -> np.ndarray:
    cls = np.full(instance.shape, AUTHORED, np.int8)
    zero = np.all(position_w == 0, axis=-1)
    cls[(instance == 0) & ~zero] = INDEX0_NONCATALOG
    cls[(instance == 0) & zero] = INDEX0_NO_GEOMETRY
    return cls


def orientation_residuals(position_w, mask, r_wh, o_w) -> dict:
    """How far each masked cell's Position direction lies outside its declared cell (contract check 2)."""
    p = head_points(position_w, r_wh, o_w)
    yaw, pitch = SP.yaw_pitch_deg(p)
    yc = SP.yaw_centers_deg()[None, :].repeat(SP.HEIGHT, 0)
    pc = SP.pitch_centers_deg()[:, None].repeat(SP.WIDTH, 1)
    dyaw = (yaw - yc + 180.0) % 360.0 - 180.0
    dpitch = pitch - pc
    tol = 1e-3
    yaw_tol = 0.25 + tol / np.maximum(np.cos(np.radians(pitch)), 1e-12)
    bad = mask & ((np.abs(dpitch) > 0.25 + tol) | (np.abs(dyaw) > yaw_tol))
    return {"cells": int(mask.sum()), "outside": int(bad.sum()),
            "max_abs_dpitch_deg": float(np.abs(dpitch[mask]).max()) if mask.any() else 0.0,
            "max_abs_dyaw_deg_below_85": float(np.abs(dyaw[mask & (np.abs(pitch) < 85)]).max())
            if (mask & (np.abs(pitch) < 85)).any() else 0.0}


# ------------------------------------------------------------------ components and seeds
def components_wrap(mask: np.ndarray, wrap: bool = True) -> tuple[int, np.ndarray]:
    """8-connected components; longitude wraps (column 0 ~ column W-1), latitude does not."""
    n, lab = cv2.connectedComponents(mask.astype(np.uint8), connectivity=8, ltype=cv2.CV_32S)
    parent = list(range(n))

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    if wrap:
        w = mask.shape[1] - 1
        for j in np.flatnonzero(mask[:, 0]).tolist():
            for j2 in (j - 1, j, j + 1):
                if 0 <= j2 < mask.shape[0] and mask[j2, w]:
                    ra, rb = find(int(lab[j, 0])), find(int(lab[j2, w]))
                    if ra != rb:
                        parent[max(ra, rb)] = min(ra, rb)
    roots = np.array([find(k) for k in range(n)], np.int32)
    lab = roots[lab]
    lab[~mask] = 0
    return len(set(roots[1:].tolist())), lab


def ordered_components(mask: np.ndarray, weights: np.ndarray) -> list[dict]:
    """Components of one object's mask in the declared order (contract 4.4)."""
    _n, lab = components_wrap(mask)
    comps = []
    for root in sorted(set(np.unique(lab[mask]).tolist())):
        rows, cols = np.nonzero(lab == root)
        row_counts = np.bincount(rows, minlength=SP.HEIGHT)
        k = int(np.lexsort((cols, rows))[0])
        comps.append({"rows": rows, "cols": cols, "cells": int(len(rows)),
                      "solid_angle_sr": SP.solid_angle(row_counts, weights),
                      "min_rc": [int(rows[k]), int(cols[k])]})
    comps.sort(key=lambda c: (-c["solid_angle_sr"], -c["cells"], c["min_rc"][0], c["min_rc"][1]))
    return comps


def representative_seed(comp: dict, dirs: np.ndarray, weights: np.ndarray) -> dict:
    """Contract 4.5 with the section-11 tie semantics: the support cell nearest the solid-angle-weighted
    mean direction; cells within SEED_TIE_DOT_EPS of the maximum dot product are tied (row, then column)."""
    rows, cols = comp["rows"], comp["cols"]
    d = dirs[rows, cols]
    m = (d * weights[rows][:, None]).sum(axis=0)
    norm = float(np.linalg.norm(m))
    if norm < SP.SEED_FALLBACK_NORM:
        r, c = comp["min_rc"]
        fallback, dot, tied = True, None, None
    else:
        m = m / norm
        dots = d @ m
        best = np.flatnonzero(dots.max() - dots <= SP.SEED_TIE_DOT_EPS)
        k = best[np.lexsort((cols[best], rows[best]))[0]]
        r, c = int(rows[k]), int(cols[k])
        fallback, dot, tied = False, float(dots[k]), int(len(best))
    return {"row": int(r), "col": int(c), "yaw_deg": float(SP.yaw_centers_deg()[c]),
            "pitch_deg": float(SP.pitch_centers_deg()[r]), "fallback": fallback,
            "mean_norm": norm, "dot_to_mean": dot, "tied_candidates": tied}


def seed_tie_control() -> list[dict]:
    """Known-answer controls of the section-11 tie rule on exactly mirror-symmetric synthetic components."""
    weights, dirs = SP.row_weights(), SP.cell_directions_h()
    out = []
    for name, cells, want in SP.SEED_TIE_CONTROLS:
        mask = np.zeros((SP.HEIGHT, SP.WIDTH), bool)
        for r, c in cells:
            mask[r, c] = True
        comps = ordered_components(mask, weights)
        seed = representative_seed(comps[0], dirs, weights)
        got = (seed["row"], seed["col"])
        out.append({"name": name, "cells": [list(c) for c in cells], "expected": list(want), "got": list(got),
                    "components": len(comps), "tied_candidates": seed["tied_candidates"],
                    "ok": got == tuple(want) and len(comps) == 1 and seed["tied_candidates"] == len(cells)})
    return out


def angular_distance_deg(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, np.float64); b = np.asarray(b, np.float64)
    return float(np.degrees(math.atan2(float(np.linalg.norm(np.cross(a, b))), float(a @ b))))


# ------------------------------------------------------------------ distributions
def binned(values, edges, weights=None) -> dict:
    v = np.asarray(values, np.float64)
    w = np.ones_like(v) if weights is None else np.asarray(weights, np.float64)
    e = np.asarray(edges, np.float64)
    k = np.searchsorted(e, v, side="right") - 1
    under = k < 0
    over = k >= len(e) - 1
    inside = ~under & ~over
    counts = np.zeros(len(e) - 1)
    np.add.at(counts, k[inside], w[inside])
    as_list = (lambda x: [int(round(c)) for c in x]) if weights is None else (lambda x: [float(c) for c in x])
    return {"edges": [float(x) if math.isfinite(x) else "inf" for x in e], "counts": as_list(counts),
            "underflow": as_list([w[under].sum()])[0], "overflow": as_list([w[over].sum()])[0]}


def weighted_quantiles(values: np.ndarray, weights: np.ndarray, qs) -> list[float]:
    order = np.argsort(values, kind="stable")
    v, w = values[order], weights[order]
    cum = np.cumsum(w)
    total = cum[-1]
    return [float(v[min(int(np.searchsorted(cum, q * total, side="left")), len(v) - 1)]) for q in qs]


# ------------------------------------------------------------------ analysis
def accepted_25() -> tuple[list[int], dict]:
    res = read_json(source_path("controller02_result"))
    seeds = read_json(source_path("seeds"))
    a = sorted(int(k) for k in res["final_states"])
    b = sorted(int(s["instance_id"]) for s in seeds["instances"])
    if a != b or len(a) != 25:
        raise SystemExit(f"{PREFIX} STOP the accepted-25 sources disagree: {a} vs {b}")
    return a, {int(s["instance_id"]): s["seed_gaze_deg"] for s in seeds["instances"]}


def analyze(run: Path) -> dict:
    sources = verify_sources(("seeds", "catalog", "controller02_result"))
    meta = read_json(run / "render/render-metadata.json")
    exr = run / "render/canonical.exr"
    if sha256(exr) != meta["exr_sha256"]:
        raise SystemExit(f"{PREFIX} STOP canonical.exr differs from the sha256 Blender recorded")
    seeds = read_json(source_path("seeds"))
    r_wh = np.asarray(seeds["head_R_wh"], np.float64)
    o_w = np.asarray(seeds["head_origin_w_m"], np.float64)
    catalog = {int(e["instance_id"]): e["object_name"] for e in read_json(source_path("catalog"))["instances"]}
    if len(catalog) != SP.CATALOG_COUNT:
        raise SystemExit(f"{PREFIX} STOP catalog has {len(catalog)} objects")
    acc25, acc_seed = accepted_25()
    tie_control = seed_tie_control()
    if not all(c["ok"] for c in tie_control):
        raise SystemExit(f"{PREFIX} STOP the seed tie-rule control failed: {tie_control}")

    g = extract_exr(exr)
    inst, pos, rgb = g["instance"], g["position_w"], g["rgb"]
    if inst.shape != (SP.HEIGHT, SP.WIDTH):
        raise SystemExit(f"{PREFIX} STOP resolution {inst.shape}")
    if not g["index_integral"]:
        raise SystemExit(f"{PREFIX} STOP Object Index is not integral")
    illegal = sorted(set(np.unique(inst).tolist()) - set(catalog) - {0})
    if illegal:
        raise SystemExit(f"{PREFIX} STOP rendered ids outside the catalog: {illegal[:20]}")
    cls = cell_classes(inst, pos)
    authored = cls == AUTHORED
    orient = orientation_residuals(pos, authored, r_wh, o_w)
    if orient["outside"]:
        raise SystemExit(f"{PREFIX} STOP orientation check failed on canonical data: {orient}")

    weights = SP.row_weights()
    dirs = SP.cell_directions_h()
    yc, pc = SP.yaw_centers_deg(), SP.pitch_centers_deg()
    rng = np.full(inst.shape, np.nan)
    has_geom = cls != INDEX0_NO_GEOMETRY
    rng[has_geom] = np.linalg.norm(pos[has_geom].astype(np.float64) - o_w, axis=-1)
    in_domain = ((yc[None, :] >= SP.DOMAIN_YAW_DEG[0]) & (yc[None, :] <= SP.DOMAIN_YAW_DEG[1])
                 & (pc[:, None] >= SP.DOMAIN_PITCH_DEG[0]) & (pc[:, None] <= SP.DOMAIN_PITCH_DEG[1]))

    comp_raster = np.zeros(inst.shape, np.int16)
    objects, comps_out, seeds_out = [], {}, []
    for oid in sorted(catalog):
        mask = inst == oid
        cells = int(mask.sum())
        rec = {"instance_id": oid, "object_name": catalog[oid], "in_accepted_localized_25": oid in acc25}
        if cells == 0:
            rec.update(status="NO_FIRST_HIT_AT_0P5_DEG", visible_cells=0, solid_angle_sr=0.0, fraction_of_4pi=0.0,
                       components=0, range_m=None, intersects_old_controller_domain=False,
                       outside_old_controller_domain_cells=0, seed=None, seed_separation_from_accepted_deg=None)
            objects.append(rec)
            continue
        rows = np.nonzero(mask)[0]
        omega = SP.solid_angle(np.bincount(rows, minlength=SP.HEIGHT), weights)
        comps = ordered_components(mask, weights)
        for k, c in enumerate(comps, start=1):
            comp_raster[c["rows"], c["cols"]] = k
        seed = representative_seed(comps[0], dirs, weights)
        sep = None
        if oid in acc_seed:
            sep = angular_distance_deg(SP.direction_h(seed["yaw_deg"], seed["pitch_deg"]),
                                       SP.direction_h(*acc_seed[oid]))
        r = rng[mask]
        rec.update(status="VISIBLE_AT_0P5_DEG", visible_cells=cells, solid_angle_sr=omega,
                   fraction_of_4pi=omega / (4.0 * math.pi), components=len(comps),
                   largest_component_cells=comps[0]["cells"], largest_component_solid_angle_sr=comps[0]["solid_angle_sr"],
                   range_m={"min": float(r.min()), "median": float(np.median(r)), "max": float(r.max())},
                   intersects_old_controller_domain=bool((mask & in_domain).any()),
                   outside_old_controller_domain_cells=int((mask & ~in_domain).sum()),
                   seed=seed, seed_separation_from_accepted_deg=sep)
        objects.append(rec)
        comps_out[str(oid)] = [{"ordinal": k, "cells": c["cells"], "solid_angle_sr": c["solid_angle_sr"],
                                "min_rc": c["min_rc"], "row_range": [int(c["rows"].min()), int(c["rows"].max())],
                                "seam_crossing": bool((c["cols"] == 0).any() and (c["cols"] == SP.WIDTH - 1).any())}
                               for k, c in enumerate(comps, start=1)]
        seeds_out.append({"instance_id": oid, "object_name": catalog[oid], **seed,
                          "component_ordinal": 1, "in_accepted_localized_25": oid in acc25,
                          "accepted_seed_gaze_deg": acc_seed.get(oid),
                          "separation_from_accepted_deg": sep})

    visible = [o for o in objects if o["visible_cells"]]
    visible.sort(key=lambda o: (-o["solid_angle_sr"], -o["visible_cells"], o["instance_id"]))
    for k, o in enumerate(visible, start=1):
        o["rank"] = k
    for o in objects:
        o.setdefault("rank", None)

    summary = summarize(objects, cls, rng, weights, authored, acc25)
    run_outputs(run, g, rng, weights, cls, comp_raster, objects, comps_out, seeds_out, summary, catalog)
    manifest = {
        "schema": "Breadth1-manifest-v1", "experiment": "Breadth-1: Classroom-234 Spherical Glance",
        "contract": "docs/classroom-oracle/breadth-1-spherical-glance-contract.md",
        "code": code_state(), "base_commit": SP.BASE_COMMIT,
        "inputs": {**sources, "canonical_exr": {"path": str(exr), "sha256": meta["exr_sha256"]},
                   "render_metadata": {"path": str(run / "render/render-metadata.json"),
                                       "sha256": sha256(run / "render/render-metadata.json")}},
        "head_R_wh": r_wh.tolist(), "head_origin_w_m": o_w.tolist(),
        "processes": [json.loads(l) for l in (run / "process-log.jsonl").read_text().splitlines() if l.strip()],
        "orientation": orient,
        "seed_tie_rule": {"SEED_TIE_DOT_EPS": SP.SEED_TIE_DOT_EPS, "control": tie_control,
                          "note": "post-run numerical clarification, contract section 11; seeds only"},
        "truth": {"render/canonical.exr": "REFERENCE / EVALUATION (Combined, Position) + ORACLE INPUT (Object Index)",
                  "glance.npz": "REFERENCE / EVALUATION (rgb, position_w) + ORACLE INPUT (instance)",
                  "range.npz": "REFERENCE / EVALUATION (range from Position) + DERIVED (weights, classes)",
                  "components.npz": SP.TRUTH_DERIVED, "object-stats.json": SP.TRUTH_DERIVED,
                  "object-stats.csv": SP.TRUTH_DERIVED, "components.json": SP.TRUTH_DERIVED,
                  "seed-directions.json": SP.TRUTH_DERIVED, "summary.json": SP.TRUTH_DERIVED,
                  "global-point-cloud.ply": "REFERENCE / EVALUATION (Position, RGB) + ORACLE INPUT (instance)"},
        "outputs": {n: sha256(run / n) for n in OUTPUT_FILES},
    }
    write_json(run / "manifest.json", manifest)
    return summary


OUTPUT_FILES = ["glance.npz", "range.npz", "components.npz", "object-stats.json", "object-stats.csv",
                "components.json", "seed-directions.json", "summary.json", "global-point-cloud.ply"]


def summarize(objects, cls, rng, weights, authored, acc25) -> dict:
    vis = [o for o in objects if o["visible_cells"]]
    nvis = len(vis)
    omegas = sorted((o["solid_angle_sr"] for o in vis), reverse=True)
    authored_omega = SP.solid_angle(np.bincount(np.nonzero(authored)[0], minlength=SP.HEIGHT), weights)
    cell_w = np.broadcast_to(weights[:, None], cls.shape)
    r = rng[authored]
    w = cell_w[authored]

    def acct(c):
        m = cls == c
        return {"cells": int(m.sum()),
                "solid_angle_sr": SP.solid_angle(np.bincount(np.nonzero(m)[0], minlength=SP.HEIGHT), weights)}

    ccount = {}
    for o in vis:
        ccount[str(o["components"])] = ccount.get(str(o["components"]), 0) + 1
    topk = {}
    for k in SP.TOP_K:
        s = float(sum(omegas[:k]))
        topk[str(k)] = {"objects": min(k, nvis), "solid_angle_sr": s, "fraction_of_4pi": s / (4 * math.pi),
                        "fraction_of_authored": s / authored_omega if authored_omega else None}
    acc_vis = [o["instance_id"] for o in objects if o["in_accepted_localized_25"] and o["visible_cells"]]
    return {
        "schema": "Breadth1-summary-v1", "truth": SP.TRUTH_DERIVED,
        "catalog_total": len(objects),
        "visible_at_0p5_deg": nvis,
        "no_first_hit_at_0p5_deg": len(objects) - nvis,
        "visible_with_multiple_components": sum(1 for o in vis if o["components"] > 1),
        "cells_total": int(cls.size),
        "cell_accounting": {"authored": acct(AUTHORED), "index0_noncatalog_geometry": acct(INDEX0_NONCATALOG),
                            "index0_no_geometry": acct(INDEX0_NO_GEOMETRY)},
        "sphere_solid_angle_sr": float(weights.sum() * SP.WIDTH),
        "support_distribution": {
            "solid_angle_sr": binned([o["solid_angle_sr"] for o in vis], SP.SOLID_ANGLE_EDGES_SR),
            "visible_cells": binned([o["visible_cells"] for o in vis], SP.CELL_COUNT_EDGES),
            "no_first_hit_objects": len(objects) - nvis},
        "range_distribution_m": {
            "cells": binned(r, SP.RANGE_EDGES_M), "solid_angle_sr": binned(r, SP.RANGE_EDGES_M, w),
            "quantiles": SP.RANGE_QUANTILES,
            "cell_quantiles": [float(x) for x in np.quantile(r, SP.RANGE_QUANTILES, method="linear")],
            "solid_angle_weighted_quantiles": weighted_quantiles(r, w, SP.RANGE_QUANTILES)},
        "top_k_cumulative_support": topk,
        "accepted_localized_25": {"total": len(acc25), "visible": len(acc_vis),
                                  "no_first_hit": sorted(set(acc25) - set(acc_vis)),
                                  "visible_outside_accepted_25": nvis - len(acc_vis)},
        "old_controller_domain": {"yaw_deg": list(SP.DOMAIN_YAW_DEG), "pitch_deg": list(SP.DOMAIN_PITCH_DEG),
                                  "visible_intersecting": sum(1 for o in vis if o["intersects_old_controller_domain"]),
                                  "visible_entirely_outside": sum(1 for o in vis if not o["intersects_old_controller_domain"]),
                                  "visible_with_any_support_outside": sum(1 for o in vis if o["outside_old_controller_domain_cells"] > 0)},
        "component_count_distribution": dict(sorted(ccount.items(), key=lambda kv: int(kv[0]))),
        "ranking": [{"rank": o["rank"], "instance_id": o["instance_id"], "object_name": o["object_name"],
                     "solid_angle_sr": o["solid_angle_sr"], "visible_cells": o["visible_cells"]}
                    for o in sorted(vis, key=lambda o: o["rank"])],
    }


def gamma_u8(rgb_linear: np.ndarray) -> np.ndarray:
    """The Visual Language 1 display transform (vl1_data.gamma_u8): clip to [0, 1], gamma 1/2.2."""
    return np.rint(np.power(np.clip(np.asarray(rgb_linear, np.float64), 0, 1), 1 / 2.2) * 255).astype(np.uint8)


def write_ply(path: Path, xyz: np.ndarray, rgb8: np.ndarray, inst: np.ndarray, rows: np.ndarray, cols: np.ndarray) -> None:
    n = len(xyz)
    header = ("ply\nformat binary_little_endian 1.0\n"
              "comment Breadth-1 Classroom-234 spherical glance: canonical first-hit Position samples of authored cells\n"
              "comment truth: REFERENCE / EVALUATION (position, rgb) + ORACLE INPUT (instance); world frame, metres\n"
              f"element vertex {n}\nproperty float x\nproperty float y\nproperty float z\n"
              "property uchar red\nproperty uchar green\nproperty uchar blue\nproperty int instance\n"
              "property ushort row\nproperty ushort col\nend_header\n").encode("ascii")
    rec = np.zeros(n, dtype=[("x", "<f4"), ("y", "<f4"), ("z", "<f4"), ("r", "u1"), ("g", "u1"), ("b", "u1"),
                             ("i", "<i4"), ("row", "<u2"), ("col", "<u2")])
    rec["x"], rec["y"], rec["z"] = xyz[:, 0], xyz[:, 1], xyz[:, 2]
    rec["r"], rec["g"], rec["b"] = rgb8[:, 0], rgb8[:, 1], rgb8[:, 2]
    rec["i"], rec["row"], rec["col"] = inst, rows, cols
    path.write_bytes(header + rec.tobytes())


def run_outputs(run, g, rng, weights, cls, comp_raster, objects, comps_out, seeds_out, summary, catalog) -> None:
    np.savez_compressed(run / "glance.npz", rgb=g["rgb"], instance=g["instance"], position_w=g["position_w"])
    np.savez_compressed(run / "range.npz", range_m=rng, cell_weights_sr=weights, cell_class=cls)
    np.savez_compressed(run / "components.npz", component_ordinal=comp_raster)
    write_json(run / "object-stats.json", {
        "schema": "Breadth1-object-stats-v1", "truth": SP.TRUTH_DERIVED,
        "sources": {"identity": SP.TRUTH_ORACLE, "range": SP.TRUTH_REFERENCE},
        "count": len(objects), "objects": objects})
    write_json(run / "components.json", {
        "schema": "Breadth1-components-v1", "truth": SP.TRUTH_DERIVED,
        "rule": "8-connected; longitude wraps (column 0 ~ 719, diagonals included); latitude does not wrap",
        "order": "solid angle desc, cells desc, smallest (row, col) asc", "objects": comps_out})
    write_json(run / "seed-directions.json", {
        "schema": "Breadth1-seed-directions-v1", "truth": SP.TRUTH_DERIVED,
        "note": "analysis only; no seed causes an observation",
        "rule": "largest component; solid-angle-weighted mean of cell-centre directions; nearest support cell "
                "(max dot, ties row then col); fallback below norm 1e-9: smallest (row, col) cell",
        "tie_semantics": {"SEED_TIE_DOT_EPS": SP.SEED_TIE_DOT_EPS,
                          "rule": "cells with max_dot - dot <= SEED_TIE_DOT_EPS are tied; smaller row, then column",
                          "status": "post-run numerical clarification (contract section 11), authorized 2026-10-03"},
        "seeds": seeds_out})
    write_json(run / "summary.json", summary)
    with open(run / "object-stats.csv", "w", newline="") as f:
        wr = csv.writer(f, lineterminator="\n")
        wr.writerow(["instance_id", "object_name", "status", "visible_cells", "solid_angle_sr", "fraction_of_4pi",
                     "components", "range_min_m", "range_median_m", "range_max_m",
                     "intersects_old_controller_domain", "in_accepted_localized_25", "seed_yaw_deg", "seed_pitch_deg",
                     "rank", "truth"])
        for o in objects:
            rm, sd = o["range_m"] or {}, o["seed"] or {}
            wr.writerow([o["instance_id"], o["object_name"], o["status"], o["visible_cells"],
                         repr(o["solid_angle_sr"]), repr(o["fraction_of_4pi"]), o["components"],
                         repr(rm["min"]) if rm else "", repr(rm["median"]) if rm else "", repr(rm["max"]) if rm else "",
                         int(o["intersects_old_controller_domain"]), int(o["in_accepted_localized_25"]),
                         repr(sd["yaw_deg"]) if sd else "", repr(sd["pitch_deg"]) if sd else "",
                         o["rank"] if o["rank"] is not None else "", SP.TRUTH_DERIVED])
    rows, cols = np.nonzero(cls == AUTHORED)
    write_ply(run / "global-point-cloud.ply", g["position_w"][rows, cols], gamma_u8(g["rgb"][rows, cols]),
              g["instance"][rows, cols], rows.astype(np.uint16), cols.astype(np.uint16))


# ------------------------------------------------------------------ synthetic plumbing test
def synthetic(run: Path) -> dict:
    run.mkdir(parents=True, exist_ok=True)
    out = run / "synthetic"
    res = blender(run, "synthetic", ["--seeds", str(source_path("seeds")), "--out", str(out)], None)
    (run / "synthetic-blender.log").write_text(res["log"])
    if res["entry"]["returncode"] != 0:
        raise SystemExit(f"{PREFIX} synthetic Blender run failed; see {run / 'synthetic-blender.log'}")
    meta = read_json(out / "synthetic-metadata.json")
    seeds = read_json(source_path("seeds"))
    r_wh = np.asarray(seeds["head_R_wh"], np.float64)
    o_w = np.asarray(seeds["head_origin_w_m"], np.float64)
    checks = []

    def check(name, ok, detail=""):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    g = extract_exr(out / "synthetic.exr")
    import OpenEXR
    with OpenEXR.File(str(out / "synthetic.exr"), separate_channels=True) as f:
        ch2 = {k: np.asarray(v.pixels) for k, v in f.channels().items()}
    ch1 = read_uncompressed_exr(str(out / "synthetic.exr"))
    check("one EXR holds Combined, Position and Object Index",
          all(any(c.endswith(s) for c in g["channels"]) for s in ("Combined.R", "Position.X", "Object Index.X")),
          str(g["channels"]))
    check("resolution 720 x 360", g["instance"].shape == (SP.HEIGHT, SP.WIDTH), str(g["instance"].shape))
    check("Object Index is integral (first sample, unfiltered)", g["index_integral"])
    check("exr_lite and OpenEXR agree bitwise on every channel",
          sorted(ch1) == sorted(ch2) and all(np.array_equal(np.asarray(ch1[k]), ch2[k]) for k in ch1), str(sorted(ch2)))
    weights, dirs = SP.row_weights(), SP.cell_directions_h()
    check("cell weights sum to 4 pi", abs(weights.sum() * SP.WIDTH - 4 * math.pi) < 1e-12,
          repr(weights.sum() * SP.WIDTH))
    inst, pos = g["instance"], g["position_w"]
    p_h = head_points(pos, r_wh, o_w)
    sc = meta["synthetic_scene"]
    for mk in sc["markers"]:
        if mk["pass_index"] == 0:
            continue
        mask = inst == mk["pass_index"]
        comps = ordered_components(mask, weights)
        seed = representative_seed(comps[0], dirs, weights)
        err = angular_distance_deg(SP.direction_h(seed["yaw_deg"], seed["pitch_deg"]),
                                   SP.direction_h(mk["yaw_deg"], mk["pitch_deg"]))
        check(f"orientation: {mk['name']} seed within 1.5 deg of yaw {mk['yaw_deg']}, pitch {mk['pitch_deg']}",
              err < 1.5, f"seed {seed['yaw_deg']:.2f}, {seed['pitch_deg']:.2f}; error {err:.3f} deg")
        inside = np.all(np.abs(p_h[mask] - np.asarray(mk["center_h_m"])) <= mk["half_size_m"] + 1e-4, axis=-1)
        check(f"first hit: {mk['name']} Position lies on its own cube", inside.all(), f"{int((~inside).sum())} outside")
    seam = inst == next(m["pass_index"] for m in sc["markers"] if m["name"] == "m_behind_seam")
    n_wrap, _ = components_wrap(seam, True)
    n_flat, _ = components_wrap(seam, False)
    check("seam: the behind marker is 1 component with wrap, 2 without", (n_wrap, n_flat) == (1, 2), f"{n_wrap}, {n_flat}")
    for wl in sc["walls"]:
        mask = inst == wl["pass_index"]
        on = np.abs(p_h[mask][:, wl["axis"]] - wl["sign"] * wl["half_size_m"]) <= 1e-4
        check(f"first hit: {wl['name']} Position lies on its wall plane", mask.any() and on.all(), f"{int((~on).sum())} off")
        mean = g["rgb"][mask].mean(axis=0)
        check(f"RGB channel order: {wl['name']} mean colour equals its emission", np.allclose(mean, wl["rgb"], atol=0.02),
              str(np.round(mean, 3).tolist()))
    cls = cell_classes(inst, pos)
    m0 = next(m for m in sc["markers"] if m["pass_index"] == 0)
    nc = cls == INDEX0_NONCATALOG
    in0 = np.all(np.abs(p_h[nc] - np.asarray(m0["center_h_m"])) <= m0["half_size_m"] + 1e-4, axis=-1)
    check("index 0 with geometry is exactly the pass-index-0 cube", nc.any() and in0.all(), f"{int(nc.sum())} cells")
    ng = cls == INDEX0_NO_GEOMETRY
    check("index 0 without geometry lies in the open floor region", ng.any() and bool((SP.pitch_centers_deg()[np.nonzero(ng)[0]] < 0).all()),
          f"{int(ng.sum())} cells")
    rng = np.linalg.norm(pos[cls != INDEX0_NO_GEOMETRY].astype(np.float64) - o_w, axis=-1)
    check("range from Position equals the head-frame norm", np.allclose(rng, np.linalg.norm(p_h[cls != INDEX0_NO_GEOMETRY], axis=-1),
                                                                       atol=1e-9))
    orient = orientation_residuals(pos, cls != INDEX0_NO_GEOMETRY, r_wh, o_w)
    check("orientation: every geometric cell's Position direction lies inside its declared cell", orient["outside"] == 0, str(orient))
    cfg = meta["config"]
    check("configuration read-back is the frozen one",
          cfg["resolution_wh"] == [SP.WIDTH, SP.HEIGHT] and cfg["camera_type"] == SP.CAMERA_TYPE
          and cfg["panorama_type"] == SP.PANORAMA_TYPE and cfg["samples"] == SP.SPP and cfg["device_backend"] == SP.DEVICE
          and not cfg["adaptive_sampling"] and not cfg["denoising"] and cfg["pixel_filter"] == SP.PIXEL_FILTER, str(cfg)[:200])
    report = {"schema": "Breadth1-synthetic-report-v1", "code": code_state(), "checks": checks,
              "passed": all(c["ok"] for c in checks), "exr_sha256": sha256(out / "synthetic.exr"),
              "note": "factory-startup plumbing scene; no Classroom"}
    write_json(out / "synthetic-report.json", report)
    for c in checks:
        print(f"{PREFIX} synthetic {'PASS' if c['ok'] else 'FAIL'} {c['name']}" + (f" ({c['detail']})" if not c["ok"] else ""))
    print(f"{PREFIX} synthetic {sum(c['ok'] for c in checks)}/{len(checks)} {'BREADTH1_SYNTHETIC_PASS' if report['passed'] else 'FAILED'}")
    return report


# ------------------------------------------------------------------ preflight and canonical render
def preflight(run: Path) -> dict:
    run.mkdir(parents=True, exist_ok=True)
    sources = verify_sources()
    res = blender(run, "preflight", ["--seeds", sources["seeds"]["path"], "--catalog", sources["catalog"]["path"],
                                     "--out", str(run / "preflight.json")], Path(sources["blend"]["path"]))
    (run / "preflight-blender.log").write_text(res["log"])
    if res["entry"]["returncode"] != 0:
        raise SystemExit(f"{PREFIX} preflight failed; see {run / 'preflight-blender.log'}")
    pf = read_json(run / "preflight.json")
    pf["code"] = res["entry"]["code"]
    pf["sources"] = sources
    write_json(run / "preflight.json", pf)
    print(f"{PREFIX} preflight ok: catalog {pf['catalog_check']['live_count']}, EYE "
          f"{pf['eye_check']['max_abs_rotation_diff']:.2g}/{pf['eye_check']['max_abs_origin_diff']:.2g}, "
          f"device {pf['config']['device_backend']}, rendered {pf['rendered']}")
    return pf


def render(run: Path) -> dict:
    code = code_state()
    if code["dirty"] or not code["pushed"]:
        raise SystemExit(f"{PREFIX} STOP the implementation must be committed and pushed before the canonical run: {code}")
    out = run / "render"
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"{PREFIX} STOP {out} exists: the canonical observation is made exactly once")
    if (run / "process-log.jsonl").exists():
        prior = [json.loads(l) for l in (run / "process-log.jsonl").read_text().splitlines() if l.strip()]
        if any(p["mode"] == "canonical" and p["returncode"] == 0 for p in prior):
            raise SystemExit(f"{PREFIX} STOP a successful canonical render is already logged")
    syn = read_json(run / "synthetic/synthetic-report.json")
    pf = read_json(run / "preflight.json")
    for name, rep in (("synthetic", syn), ("preflight", pf)):
        if rep["code"]["commit"] != code["commit"] or rep["code"]["dirty"]:
            raise SystemExit(f"{PREFIX} STOP the {name} step did not run at this commit {code['commit']}")
    if not syn["passed"] or pf["rendered"] or not pf["catalog_check"]["equal"]:
        raise SystemExit(f"{PREFIX} STOP synthetic/preflight not passed")
    sources = verify_sources()
    res = blender(run, "canonical", ["--seeds", sources["seeds"]["path"], "--catalog", sources["catalog"]["path"],
                                     "--out", str(out)], Path(sources["blend"]["path"]))
    out.mkdir(parents=True, exist_ok=True)
    (out / "blender.log").write_text(res["log"])
    if res["entry"]["returncode"] != 0:
        raise SystemExit(f"{PREFIX} canonical render FAILED technically; see {out / 'blender.log'}")
    meta = read_json(out / "render-metadata.json")
    print(f"{PREFIX} canonical render: {meta['render_seconds']} s on {meta['config']['device_backend']}, "
          f"exr sha256 {meta['exr_sha256']}, wall {res['entry']['seconds']} s")
    return meta


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("synthetic", "preflight", "render", "analyze", "visualize"):
        p = sub.add_parser(name)
        p.add_argument("--run", required=True, type=Path)
        if name == "visualize":
            p.add_argument("--visuals", required=True, type=Path)
    a = ap.parse_args(argv)
    run = a.run.resolve()
    if a.cmd == "synthetic":
        return 0 if synthetic(run)["passed"] else 1
    if a.cmd == "preflight":
        preflight(run)
    elif a.cmd == "render":
        render(run)
    elif a.cmd == "analyze":
        t0 = time.perf_counter()
        s = analyze(run)
        print(f"{PREFIX} analyze: catalog {s['catalog_total']}, visible {s['visible_at_0p5_deg']}, no first hit "
              f"{s['no_first_hit_at_0p5_deg']}, multi-component {s['visible_with_multiple_components']} "
              f"({time.perf_counter() - t0:.1f} s)")
    elif a.cmd == "visualize":
        import breadth1_visuals
        breadth1_visuals.visualize(run, a.visuals.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
