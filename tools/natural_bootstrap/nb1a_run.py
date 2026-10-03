"""Natural Bootstrap-1a: spherical range connectivity (run order, the three separated paths).

Contract: docs/natural-bootstrap/nb1a-range-connectivity-contract.md.

    .venv/bin/python tools/natural_bootstrap/nb1a_run.py synthetic     --run RUN
    .venv/bin/python tools/natural_bootstrap/nb1a_run.py prepare-input --run RUN
    .venv/bin/python tools/natural_bootstrap/nb1a_run.py discover      --run RUN
    .venv/bin/python tools/natural_bootstrap/nb1a_run.py freeze        --run RUN
    .venv/bin/python tools/natural_bootstrap/nb1a_run.py evaluate      --run RUN
    .venv/bin/python tools/natural_bootstrap/nb1a_run.py visualize     --run RUN --visuals VIS

The three paths run under ``nb1a_guard.OpenGuard``:
- ``prepare-input`` reads only the accepted canonical EXR (Combined + Position) and the head pose.
- ``discover`` reads only ``input/range-sensory.npz``.
- ``evaluate`` reads Object Index, the catalog and RGB only after it has verified the freeze.
No Blender process and no controller run.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))  # tools/: exr_lite (accepted pure-Python reader; its opens are guard-visible)

import nb1a_discovery as D  # noqa: E402
import nb1a_spec as SP  # noqa: E402
from exr_lite import read_uncompressed_exr  # noqa: E402
from nb1a_guard import OpenGuard  # noqa: E402

PREFIX = "[nb1a]"
FROZEN = ["../input/range-sensory.npz", "continuity-edges.npz", "hypothesis-raster.npz", "hypotheses.json",
          "hypotheses.csv", "seeds.json", "discovery-summary.json", "discovery-opened-files.json"]
DISCOVERY_CODE = ["nb1a_spec.py", "nb1a_discovery.py", "nb1a_guard.py"]


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


def verify_source(key: str) -> Path:
    path, want = SP.SOURCES[key]
    got = sha256(path)
    if got != want:
        raise SystemExit(f"{PREFIX} STOP source {key} sha256 {got} != accepted {want}")
    return Path(path)


def srgb_encode(lin: np.ndarray) -> np.ndarray:
    c = np.clip(np.asarray(lin, np.float64), 0.0, 1.0)
    s = np.where(c <= 0.0031308, 12.92 * c, 1.055 * np.power(c, 1 / 2.4) - 0.055)
    return np.rint(s * 255.0).astype(np.uint8)


def srgb_decode(s8: np.ndarray) -> np.ndarray:
    c = np.asarray(s8, np.float64) / 255.0
    return np.where(c <= 0.04045, c / 12.92, np.power((c + 0.055) / 1.055, 2.4))


# ------------------------------------------------------------------ path 1: sensory-proxy preparation
def prepare_input(run: Path) -> dict:
    exr, seeds = Path(SP.SOURCES["exr"][0]), Path(SP.SOURCES["seeds"][0])
    out = run / "input"
    out.mkdir(parents=True, exist_ok=True)
    with OpenGuard("prepare-input", [exr, seeds], [out]) as g:
        verify_source("exr"), verify_source("seeds")
        pose = json.loads(seeds.read_text())
        o_w = np.asarray(pose["head_origin_w_m"], np.float64)
        ch = read_uncompressed_exr(str(exr))

        def one(suffix):   # only Combined RGB and Position are ever accessed
            keys = [k for k in ch if k.endswith(suffix)]
            if len(keys) != 1:
                raise RuntimeError(f"expected one channel ending {suffix!r}: {keys}")
            return np.asarray(ch[keys[0]])

        rgb_lin = np.stack([one(f"Combined.{c}") for c in "RGB"], -1).astype(np.float32)
        pos = np.stack([one(f"Position.{c}") for c in "XYZ"], -1).astype(np.float32)
        del ch
        valid = ~np.all(pos == 0, axis=-1)
        rng = np.zeros(valid.shape, np.float64)
        rng[valid] = np.linalg.norm(pos[valid].astype(np.float64) - o_w, axis=-1)
        if rng.shape != (SP.HEIGHT, SP.WIDTH):
            raise SystemExit(f"{PREFIX} STOP sensory input is {rng.shape}")
        np.savez_compressed(out / "range-sensory.npz", range_m=rng, valid_mask=valid)
        np.savez_compressed(out / "rgb-sensory.npz", srgb8=srgb_encode(rgb_lin))
    rec = g.record()
    write_json(out / "input-opened-files.json", rec)
    if rec["violations"]:
        raise SystemExit(f"{PREFIX} STOP input preparation guard violations: {rec['violations']}")
    manifest = {
        "schema": "NB1a-input-manifest-v1", "truth": SP.TRUTH_ORACLE,
        "statement": "controlled sensory proxy derived from the Blender Combined + Position passes of the accepted "
                     "Breadth-1 observation; not natural stereo sensing",
        "sources": {"canonical_exr": {"path": str(exr), "sha256": SP.SOURCES["exr"][1],
                                      "channels_used": ["Combined.R", "Combined.G", "Combined.B", "Position.X",
                                                        "Position.Y", "Position.Z"]},
                    "head_pose": {"path": str(seeds), "sha256": SP.SOURCES["seeds"][1],
                                  "fields_used": ["head_origin_w_m"]}},
        "head_origin_w_m": o_w.tolist(),
        "range_definition": "||position_w - head_origin_w_m||; valid iff Position != (0, 0, 0); 0 where invalid",
        "rgb_definition": "standard sRGB transfer of clip(Combined linear, 0, 1), 8-bit; diagnostics/visuals only",
        "grid": {"width": SP.WIDTH, "height": SP.HEIGHT, "cell_deg": SP.CELL_DEG,
                 "yaw": "-180 + 0.5 (i + 0.5)", "pitch": "90 - 0.5 (j + 0.5)", "frame": "head (+X right, +Y up, -Z forward)"},
        "files": {"range-sensory.npz": {"arrays": ["range_m", "valid_mask"], "sha256": sha256(out / "range-sensory.npz")},
                  "rgb-sensory.npz": {"arrays": ["srgb8"], "sha256": sha256(out / "rgb-sensory.npz")}},
        "code": code_state(),
    }
    write_json(out / "input-manifest.json", manifest)
    print(f"{PREFIX} prepare-input: {int(valid.sum())} valid of {valid.size} cells; guard data reads "
          f"{len(rec['data_reads'])}, violations 0")
    return manifest


# ------------------------------------------------------------------ path 2: discovery
def write_discovery(out: Path, res: dict, valid: np.ndarray) -> None:
    e = res["edges"]
    np.savez_compressed(out / "continuity-edges.npz", a=e["a"], b=e["b"], delta=e["delta"], C=e["C"],
                        retained=e["retained"])
    np.savez_compressed(out / "hypothesis-raster.npz", labels=res["labels"], boundary=res["boundary"],
                        clearance_rad=res["clearance"])
    write_json(out / "hypotheses.json", {"schema": "NB1a-hypotheses-v1", "truth": SP.TRUTH_DERIVED,
                                         "config": SP.DISCOVERY_CONFIG, "count": len(res["hypotheses"]),
                                         "hypotheses": res["hypotheses"]})
    with open(out / "hypotheses.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["id", "cells", "support_sr", "fraction_of_4pi", "range_min_m", "range_median_m", "range_max_m",
                    "boundary_cells", "max_interior_clearance_deg", "seed_row", "seed_col", "seed_yaw_deg",
                    "seed_pitch_deg", "seed_range_m", "fallback", "tied_candidates", "truth"])
        for h in res["hypotheses"]:
            s, r = h["seed"], h["range_m"]
            w.writerow([h["id"], h["cells"], repr(h["support_sr"]), repr(h["fraction_of_4pi"]), repr(r["min"]),
                        repr(r["median"]), repr(r["max"]), h["boundary_cells"],
                        "" if h["max_interior_clearance_deg"] is None else repr(h["max_interior_clearance_deg"]),
                        s["row"], s["col"], repr(s["yaw_deg"]), repr(s["pitch_deg"]), repr(s["range_m"]),
                        s["fallback"] or "", "" if s["tied_candidates"] is None else s["tied_candidates"],
                        SP.TRUTH_DERIVED])
    write_json(out / "seeds.json", {
        "schema": "NB1a-seeds-v1", "truth": SP.TRUTH_DERIVED,
        "note": "deep-interior seeds for later active interrogation; no seed causes an observation in NB1a",
        "rule": SP.DISCOVERY_CONFIG["seed"],
        "seeds": [{"id": h["id"], **h["seed"], "cells": h["cells"]} for h in res["hypotheses"]]})


def discover(run: Path) -> dict:
    out = run / "discovery"
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"{PREFIX} STOP {out} exists: the canonical discovery is made once")
    out.mkdir(parents=True, exist_ok=True)
    src = run / "input/range-sensory.npz"
    t0 = time.perf_counter()
    with OpenGuard("discovery", [src], [out]) as g:
        rng, valid = D.load_range_input(src)
        res = D.discover(rng, valid)
        n_pairs = len(SP.neighbor_pairs()[0])
        write_discovery(out, res, valid)
        summ = D.summary(res, valid, n_pairs)
        summ["seconds"] = round(time.perf_counter() - t0, 2)
        write_json(out / "discovery-summary.json", summ)
    rec = g.record()
    rec["truth_firewall_violations"] = len(rec["violations"])
    write_json(out / "discovery-opened-files.json", rec)
    if rec["violations"]:
        raise SystemExit(f"{PREFIX} STOP discovery truth-firewall violations: {rec['violations']}")
    print(f"{PREFIX} discover: {summ['valid_cells']} valid cells, {summ['candidate_pairs']} candidate pairs, "
          f"{summ['retained_edges']} retained / {summ['cut_edges']} cut; {summ['hypotheses']} hypotheses "
          f"({summ['singletons']} singletons); largest {summ['largest_fraction_of_4pi']:.4f} of 4pi; "
          f"guard data reads {rec['data_reads']}; violations 0 ({summ['seconds']} s)")
    return summ


def freeze(run: Path) -> dict:
    out = run / "discovery"
    rec = {"schema": "NB1a-bootstrap-freeze-v1", "truth": SP.TRUTH_DERIVED,
           "files": {n: sha256(out / n) for n in FROZEN},
           "discovery_config": SP.DISCOVERY_CONFIG,
           "discovery_config_sha256": hashlib.sha256(json.dumps(SP.DISCOVERY_CONFIG, sort_keys=True).encode()).hexdigest(),
           "discovery_code": {n: sha256(HERE / n) for n in DISCOVERY_CODE}, "code": code_state(),
           "frozen_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    write_json(out / "bootstrap-freeze.json", rec)
    print(f"{PREFIX} freeze: {len(rec['files'])} products hashed")
    return rec


def verify_freeze(run: Path) -> dict:
    out = run / "discovery"
    fz = read_json(out / "bootstrap-freeze.json")
    bad = [n for n, h in fz["files"].items() if sha256(out / n) != h]
    if bad or set(fz["files"]) != set(FROZEN):
        raise SystemExit(f"{PREFIX} STOP frozen bootstrap products do not verify: {bad}")
    return fz


# ------------------------------------------------------------------ path 3: reference / evaluation
def evaluate(run: Path) -> dict:
    dsc, out = run / "discovery", run / "evaluation"
    out.mkdir(parents=True, exist_ok=True)
    exr, catalog_p, b1 = (Path(SP.SOURCES[k][0]) for k in ("exr", "catalog", "breadth1_summary"))
    frozen_paths = [dsc / n for n in FROZEN] + [dsc / "bootstrap-freeze.json"]
    with OpenGuard("evaluation", frozen_paths + [exr, catalog_p, b1, run / "input/rgb-sensory.npz"], [out]) as g:
        fz = verify_freeze(run)
        g.mark("freeze_verified")
        with np.load(dsc / "hypothesis-raster.npz") as z:
            labels = z["labels"]
        with np.load(dsc / "continuity-edges.npz") as z:
            ea, eb, retained = z["a"], z["b"], z["retained"]
        hyps = read_json(dsc / "hypotheses.json")["hypotheses"]
        g.mark("reference_access_begins")
        verify_source("exr"), verify_source("catalog"), verify_source("breadth1_summary")
        ch = read_uncompressed_exr(str(exr))
        key = [k for k in ch if k.endswith("Object Index.X")]
        oid = np.rint(np.asarray(ch[key[0]])).astype(np.int64)
        del ch
        np.savez_compressed(out / "reference-cells.npz", object_index=oid.astype(np.int32),
                            o0_mask=(labels > 0) & (oid == 0))
        catalog = {int(e["instance_id"]): e["object_name"] for e in json.loads(catalog_p.read_text())["instances"]}
        b1sum = json.loads(b1.read_text())
        ov = overlap(labels, oid, hyps, catalog, b1sum)
        np.savez_compressed(out / "overlap-matrix.npz", h=ov.pop("_h"), o=ov.pop("_o"), cells=ov.pop("_cells"),
                            support_sr=ov.pop("_sr"))
        write_json(out / "overlap-summary.json", ov)
        with np.load(run / "input/rgb-sensory.npz") as z:
            srgb8 = z["srgb8"]
        rgbd = rgb_diagnostics(srgb8, labels, ea, eb, retained, fz)
        np.savez_compressed(out / "rgb-edge-contrast.npz", contrast=rgbd.pop("_contrast"),
                            intra_max=rgbd.pop("_intra_max"), cut_max=rgbd.pop("_cut_max"))
        write_json(out / "rgb-edge-diagnostics.json", rgbd)
    rec = g.record()
    order = [e.get("label") or e.get("path") for e in rec["events"] if e.get("event") == "mark" or e.get("kind") == "data-read"]
    rec["ordered_data_events"] = order
    write_json(out / "evaluation-opened-files.json", rec)
    after = verify_freeze(run)
    if rec["violations"]:
        raise SystemExit(f"{PREFIX} STOP evaluation guard violations: {rec['violations']}")
    print(f"{PREFIX} evaluate: overlap pairs {ov['pairs']}; O_0 cells {ov['accounting']['O0_cells']}; frozen products "
          f"re-verified ({len(after['files'])})")
    return ov


def overlap(labels: np.ndarray, oid: np.ndarray, hyps: list[dict], catalog: dict, b1sum: dict) -> dict:
    lab = labels.reshape(-1)
    o = oid.reshape(-1)
    cells = np.flatnonzero(lab > 0)
    key = lab[cells].astype(np.int64) * 100000 + o[cells]
    order = np.argsort(key, kind="stable")
    cells, key = cells[order], key[order]
    starts = np.flatnonzero(np.r_[True, key[1:] != key[:-1]])
    ends = np.r_[starts[1:], len(key)]
    H, O, C, A = [], [], [], []
    for s, e in zip(starts.tolist(), ends.tolist()):
        k = int(key[s])
        H.append(k // 100000); O.append(k % 100000); C.append(e - s)
        A.append(SP.support_sr(np.bincount(cells[s:e] // SP.WIDTH, minlength=SP.HEIGHT)))
    H, O, C, A = np.array(H, np.int32), np.array(O, np.int32), np.array(C, np.int64), np.array(A, np.float64)
    sup = {h["label"]: h["support_sr"] for h in hyps}
    ids = {h["label"]: h["id"] for h in hyps}
    per_h = []
    for h in hyps:
        m = H == h["label"]
        oo, aa = O[m], A[m]
        idx = np.argsort(-aa, kind="stable")
        fr = [{"o": int(oo[i]), "name": catalog.get(int(oo[i]), "O_0 (index 0, noncatalog geometry)"),
               "fraction": float(aa[i] / sup[h["label"]])} for i in idx]
        per_h.append({"id": h["id"], "support_sr": h["support_sr"], "authored_ids_intersected": int((oo > 0).sum()),
                      "reference_ids_intersected": int(len(oo)), "dominant": fr[0] if fr else None,
                      "O0_fraction": float(aa[oo == 0].sum() / sup[h["label"]]) if (oo == 0).any() else 0.0,
                      "fractions": fr[:8]})
    per_o = []
    for j in sorted(set(O.tolist())):
        m = O == j
        hh, aa = H[m], A[m]
        idx = np.argsort(-aa, kind="stable")
        tot = float(math.fsum(aa.tolist()))
        per_o.append({"o": int(j), "name": catalog.get(int(j), "O_0 (index 0, noncatalog geometry)"),
                      "support_sr": tot, "hypotheses_intersecting": int(len(hh)),
                      "largest_share": float(aa[idx[0]] / tot),
                      "distribution": [{"id": ids[int(hh[i])], "support_sr": float(aa[i]), "fraction": float(aa[i] / tot)}
                                       for i in idx[:10]]})
    o0_cells = int(C[O == 0].sum())
    cat_cells = int(C[O > 0].sum())
    acct = {"valid_cells": int(len(cells)), "catalog_cells": cat_cells, "O0_cells": o0_cells,
            "breadth1_authored_cells": b1sum["cell_accounting"]["authored"]["cells"],
            "breadth1_O0_cells": b1sum["cell_accounting"]["index0_noncatalog_geometry"]["cells"],
            "matches_breadth1": cat_cells == b1sum["cell_accounting"]["authored"]["cells"]
            and o0_cells == b1sum["cell_accounting"]["index0_noncatalog_geometry"]["cells"]}
    one_to_many = sorted(per_h, key=lambda r: (-r["authored_ids_intersected"], -r["support_sr"]))[:8]
    many_to_one = sorted([r for r in per_o if r["o"] > 0], key=lambda r: (-r["hypotheses_intersecting"], -r["support_sr"]))[:8]
    o0_dom = sorted(per_h, key=lambda r: (-r["O0_fraction"] * r["support_sr"], r["id"]))[:8]
    return {
        "schema": "NB1a-overlap-summary-v1", "truth": SP.TRUTH_REFERENCE,
        "statement": "descriptive comparison of the frozen natural decomposition with authored Blender identity; "
                     "not a ground-truth confusion matrix; no precision / recall / accuracy / IoU",
        "pairs": int(len(H)), "accounting": acct,
        "authored_ids_touched": int(len(set(O.tolist()) - {0})),
        "hypotheses_touching_O0": int(len(set(H[O == 0].tolist()))),
        "examples": {"one_natural_to_many_authored": [{k: r[k] for k in ("id", "support_sr", "authored_ids_intersected", "dominant")} for r in one_to_many],
                     "many_natural_to_one_authored": [{k: r[k] for k in ("o", "name", "support_sr", "hypotheses_intersecting", "largest_share")} for r in many_to_one],
                     "natural_dominated_by_O0": [{k: r[k] for k in ("id", "support_sr", "O0_fraction", "dominant")} for r in o0_dom]},
        "per_hypothesis": per_h, "per_reference_id": per_o,
        "_h": H, "_o": O, "_cells": C, "_sr": A,
    }


def rgb_diagnostics(srgb8: np.ndarray, labels: np.ndarray, ea, eb, retained, fz: dict) -> dict:
    lin = srgb_decode(srgb8).reshape(-1, 3)
    contrast = np.linalg.norm(lin[ea] - lin[eb], axis=1)
    intra = np.zeros(labels.size); cut = np.zeros(labels.size)
    np.maximum.at(intra, ea[retained], contrast[retained]); np.maximum.at(intra, eb[retained], contrast[retained])
    np.maximum.at(cut, ea[~retained], contrast[~retained]); np.maximum.at(cut, eb[~retained], contrast[~retained])

    def dist(v):
        return {"edges_n": int(len(v)), "binned": D.binned(v, SP.RGB_CONTRAST_EDGES, zero_separate=True),
                "quantiles": D.quantiles(v), "mean": float(v.mean()) if len(v) else None}
    return {"schema": "NB1a-rgb-edge-diagnostics-v1", "truth": SP.TRUTH_DERIVED,
            "statement": "post-freeze descriptive diagnostic; RGB caused no merge, split, seed change or deletion",
            "contrast": "|| sRGB-decoded linear rgb_i - rgb_j ||_2 over every candidate neighbour pair; no threshold",
            "computed_after_freeze": True, "frozen_inputs_sha256": fz["files"],
            "retained": dist(contrast[retained]), "cut": dist(contrast[~retained]),
            "quantiles": SP.QUANTILES, "_contrast": contrast,
            "_intra_max": intra.reshape(labels.shape), "_cut_max": cut.reshape(labels.shape)}


# ------------------------------------------------------------------ synthetic known-answer shapes
def synthetic_shapes() -> list[dict]:
    """Known-answer rasters (no Blender, no Classroom).  Returns (name, range, valid, expectation)."""
    H, W = SP.HEIGHT, SP.WIDTH
    out = []

    def blank():
        return np.zeros((H, W)), np.zeros((H, W), bool)

    r, v = blank(); r[170:190, 350:370] = 2.0; v[170:190, 350:370] = True
    out.append(("fronto-parallel patch", r, v, {"hypotheses": 1}))
    r, v = blank(); r[170:190, 350:360] = 2.0; r[170:190, 360:370] = 3.0; v[170:190, 350:370] = True
    out.append(("clean depth step", r, v, {"hypotheses": 2}))
    d = SP.cell_directions_h()
    for theta, want in ((73.5, 1), (76.5, 3)):
        r, v = blank()
        cols = [359, 360, 361]
        d0 = d[180, 360]
        t = math.radians(theta)
        # plane normal in the horizontal plane at angle theta from the central ray d0
        az0 = math.atan2(d0[0], -d0[2])
        n = np.array([math.sin(az0 + t), 0.0, -math.cos(az0 + t)])
        h = 2.0 * float(n @ d0)
        for c in cols:
            r[180, c] = h / float(n @ d[180, c]); v[180, c] = True
        out.append((f"{theta} deg slanted strip", r, v, {"hypotheses": want}))
    r, v = blank(); r[175:185, 715:720] = 2.0; r[175:185, 0:5] = 2.0; v[175:185, 715:720] = True; v[175:185, 0:5] = True
    out.append(("longitude seam patch", r, v, {"hypotheses": 1, "no_wrap_hypotheses": 2}))
    r, v = blank(); r[180, 400] = r[181, 401] = 2.0; v[180, 400] = v[181, 401] = True
    out.append(("diagonal pair", r, v, {"hypotheses": 1}))
    r, v = blank(); r[100, 100] = 2.0; v[100, 100] = True
    out.append(("singleton", r, v, {"hypotheses": 1, "seed": (100, 100), "clearance": 0.0}))
    r, v = blank(); r[170:191, 350:371] = 2.0; v[170:191, 350:371] = True
    out.append(("deep-interior square", r, v, {"hypotheses": 1, "seed": (180, 360), "tied": 1}))
    r, v = blank(); r[170:190, 350:370] = 2.0; v[170:190, 350:370] = True
    out.append(("symmetric four-way seed tie", r, v, {"hypotheses": 1, "seed": (179, 359), "tied": 4}))
    r = np.full((H, W), 2.0); v = np.ones((H, W), bool)
    out.append(("no-boundary full sphere", r, v, {"hypotheses": 1, "seed": (0, 0), "fallback": "NO_BOUNDARY_FALLBACK"}))
    return out


def synthetic(run: Path) -> dict:
    out = run / "synthetic"
    out.mkdir(parents=True, exist_ok=True)
    results = []
    for name, r, v, want in synthetic_shapes():
        res = D.discover(r, v)
        h = res["hypotheses"]
        got = {"hypotheses": len(h)}
        ok = len(h) == want["hypotheses"]
        if "seed" in want:
            s = h[0]["seed"]
            got.update(seed=[s["row"], s["col"]], clearance=s["clearance_rad"], tied=s["tied_candidates"],
                       fallback=s["fallback"])
            ok = ok and (s["row"], s["col"]) == tuple(want["seed"])
            if "clearance" in want:
                ok = ok and s["clearance_rad"] == want["clearance"]
            if "tied" in want:
                ok = ok and s["tied_candidates"] == want["tied"]
            if "fallback" in want:
                ok = ok and s["fallback"] == want["fallback"]
        if "no_wrap_hypotheses" in want:
            got["no_wrap_hypotheses"] = len(D.discover(r, v, wrap=False)["hypotheses"])
            ok = ok and got["no_wrap_hypotheses"] == want["no_wrap_hypotheses"]
        if "slanted" in name:
            got["C"] = [float(x) for x in res["edges"]["C"]]
        results.append({"name": name, "expected": {k: list(x) if isinstance(x, tuple) else x for k, x in want.items()},
                        "got": got, "ok": bool(ok)})
        print(f"{PREFIX} synthetic {'PASS' if ok else 'FAIL'} {name}: {got}")
    report = {"schema": "NB1a-synthetic-report-v1", "code": code_state(), "C_MAX": SP.C_MAX, "cases": results,
              "passed": all(x["ok"] for x in results), "note": "known-answer rasters; no Blender, no Classroom"}
    write_json(out / "synthetic-report.json", report)
    print(f"{PREFIX} synthetic {sum(x['ok'] for x in results)}/{len(results)} "
          f"{'NB1A_SYNTHETIC_PASS' if report['passed'] else 'FAILED'}")
    return report


# ------------------------------------------------------------------ manifest
def write_manifest(run: Path) -> dict:
    files = sorted(str(p.relative_to(run)) for p in run.rglob("*") if p.is_file()
                   and p.name not in ("manifest.json", "check-summary.json", "process-log.jsonl"))
    m = {"schema": "NB1a-manifest-v1", "experiment": "Natural Bootstrap-1a: Spherical Range Connectivity",
         "contract": "docs/natural-bootstrap/nb1a-range-connectivity-contract.md", "code": code_state(),
         "base_commit": SP.BASE_COMMIT, "sources": {k: {"path": str(p), "sha256": h} for k, (p, h) in SP.SOURCES.items()},
         "truth": {"input/": SP.TRUTH_ORACLE, "discovery/": SP.TRUTH_DERIVED,
                   "evaluation/overlap-*": SP.TRUTH_REFERENCE, "evaluation/rgb-edge-*": SP.TRUTH_DERIVED},
         "files": {f: sha256(run / f) for f in files}}
    write_json(run / "manifest.json", m)
    return m


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("synthetic", "prepare-input", "discover", "freeze", "evaluate", "visualize"):
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
        if a.cmd == "prepare-input":
            prepare_input(run)
        elif a.cmd == "discover":
            discover(run)
        elif a.cmd == "freeze":
            freeze(run)
        elif a.cmd == "evaluate":
            evaluate(run)
        elif a.cmd == "visualize":
            import nb1a_visuals
            nb1a_visuals.visualize(run, a.visuals.resolve())
            write_manifest(run)
        status = "ok"
        return 0
    finally:
        log_process(run, a.cmd, t0, status)


if __name__ == "__main__":
    raise SystemExit(main())
