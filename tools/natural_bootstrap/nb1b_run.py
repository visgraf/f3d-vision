"""Natural Bootstrap-1b: foveal serviceability of the frozen NB1a seeds (run order and truth boundary).

Contract: docs/natural-bootstrap/nb1b-foveal-serviceability-contract.md.

    .venv/bin/python tools/natural_bootstrap/nb1b_run.py synthetic --run RUN
    .venv/bin/python tools/natural_bootstrap/nb1b_run.py select    --run RUN
    .venv/bin/python tools/natural_bootstrap/nb1b_run.py freeze    --run RUN
    .venv/bin/python tools/natural_bootstrap/nb1b_run.py evaluate  --run RUN
    .venv/bin/python tools/natural_bootstrap/nb1b_run.py visualize --run RUN --visuals VIS

The two data paths run under the accepted ``nb1a_guard.OpenGuard``:
- ``select`` reads only the five pinned NB1a discovery products (no RGB, no Object Index, no catalog, no
  evaluation product);
- ``evaluate`` reads the NB1a RGB proxy and reference products only after it has verified the serviceability
  freeze.
No scene observation, no Blender process and no controller run.  No seed is moved and no hypothesis changed.
"""
from __future__ import annotations

import argparse
import csv
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

import nb1a_spec as A  # noqa: E402  (accepted NB1a grid geometry, read-only)
import nb1b_serviceability as S  # noqa: E402
import nb1b_spec as SP  # noqa: E402
from nb1a_guard import OpenGuard  # noqa: E402  (accepted allowlist file-open guard, read-only)

PREFIX = "[nb1b]"
FROZEN = ["../source/nb1a-source-manifest.json", "serviceability.json", "serviceability.csv", "primary-look-queue.json",
          "secondary-look-queue.json", "environment-candidate.json", "footprint-stats.json", "footprints.npz",
          "selection-summary.json", "selection-opened-files.json"]
SELECTION_CODE = {"nb1b_spec.py": HERE / "nb1b_spec.py", "nb1b_serviceability.py": HERE / "nb1b_serviceability.py",
                  "nb1a_spec.py": HERE / "nb1a_spec.py", "nb1a_discovery.py": HERE / "nb1a_discovery.py",
                  "nb1a_guard.py": HERE / "nb1a_guard.py", "fsg_geometry.py": SP.SENSOR_SOURCE}
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


# ------------------------------------------------------------------ path 1: selection (sections 2-10)
def verify_selection_inputs(disc: Path) -> dict:
    got = {n: sha256(disc / n) for n in SP.SELECTION_INPUTS}
    bad = {n: h for n, h in got.items() if h != SP.SELECTION_INPUTS[n]}
    if bad:
        raise SystemExit(f"{PREFIX} STOP NB1a source hash mismatch: {bad}")
    fz = read_json(disc / "bootstrap-freeze.json")
    off = [n for n in SP.SELECTION_INPUTS if n != "bootstrap-freeze.json" and fz["files"].get(n) != got[n]]
    if off:
        raise SystemExit(f"{PREFIX} STOP inputs disagree with the NB1a freeze record: {off}")
    return {"hashes": got, "freeze": fz}


def verify_sensor() -> str:
    h = sha256(SP.SENSOR_SOURCE)
    if h != SP.SENSOR_SOURCE_SHA256 or SP.CORE_FOV_DEG != 12.0:
        raise SystemExit(f"{PREFIX} STOP accepted sensor source changed: sha256 {h}, CORE_FOV_DEG {SP.CORE_FOV_DEG}")
    return h


def write_selection(out: Path, res: dict) -> None:
    recs = res["records"]
    write_json(out / "serviceability.json", {
        "schema": "NB1b-serviceability-v1", "truth": SP.TRUTH_DERIVED, "config": SP.SELECTION_CONFIG,
        "statement": "every accepted NB1a hypothesis classified exactly once at its unchanged NB1a seed; no observation, "
                     "no score, not objectness",
        "count": len(recs), "classes": SP.CLASSES, "hypotheses": recs})
    with open(out / "serviceability.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["id", "class", "queue", "rank", "cells", "support_sr", "clearance_deg", "seed_row", "seed_col",
                    "seed_yaw_deg", "seed_pitch_deg", "seed_range_m", "center_total", "center_own", "center_other",
                    "center_invalid", "center_safe", "full_total", "full_own", "full_other", "full_invalid", "full_safe",
                    "truth"])
        for r in recs:
            s, c, u, q = r["seed"], r["center"], r["full"], r["queue"] or {}
            w.writerow([r["id"], r["class"], q.get("name", ""), q.get("rank", ""), r["cells"], repr(r["support_sr"]),
                        "" if r["clearance_deg"] is None else repr(r["clearance_deg"]), s["row"], s["col"],
                        repr(s["yaw_deg"]), repr(s["pitch_deg"]), repr(s["range_m"]), c["total_cells"], c["own_cells"],
                        c["other_cells"], c["invalid_cells"], c["safe"], u["total_cells"], u["own_cells"], u["other_cells"],
                        u["invalid_cells"], u["safe"], SP.TRUTH_DERIVED])
    for name, cls in (("primary", SP.PRIMARY), ("secondary", SP.SECONDARY)):
        write_json(out / f"{name}-look-queue.json", {
            "schema": "NB1b-look-queue-v1", "truth": SP.TRUTH_DERIVED, "class": cls,
            "order": SP.SELECTION_CONFIG["queue_order"],
            "note": "a frozen foreground queue; no entry causes an observation in NB1b; no learned or weighted score",
            "count": len(res["queues"][name]), "queue": res["queues"][name]})
    env = [r for r in recs if r["class"] == SP.ENVIRONMENT]
    write_json(out / "environment-candidate.json", {
        "schema": "NB1b-environment-candidate-v1", "truth": SP.TRUTH_DERIVED, "rule": SP.SELECTION_CONFIG["environment"],
        "threshold_sr": SP.ENV_SUPPORT_SR,
        "note": "ENVIRONMENT_CANDIDATE != semantic background: the hypothesis occupies more than half of all viewing "
                "directions and is treated separately from localized foreground hypotheses; not queued, not deleted",
        "count": len(env), "candidates": env})
    write_json(out / "footprint-stats.json", {
        "schema": "NB1b-footprint-stats-v1", "truth": SP.TRUTH_DERIVED, "sensor": SP.SENSOR_CONSTANTS,
        "radii_used": res["radii"],
        "storage": "footprints.npz: CSR cell lists in NB1a label order (center_ptr/center_cells, full_ptr/full_cells) "
                   "and full_alpha (alpha_i of each FULL cell, rad)",
        "hypotheses": [{"id": r["id"], "label": r["label"], "center": r["center"], "full": r["full"]} for r in recs]})
    np.savez_compressed(out / "footprints.npz", **S.pack_footprints(res["footprints"]))


def select(run: Path) -> dict:
    src, out = run / "source", run / "selection"
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"{PREFIX} STOP {out} exists: the canonical selection is made once")
    src.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    disc = SP.NB1A_RUN / "discovery"
    code = code_state()
    t0 = time.perf_counter()
    with OpenGuard("selection", [disc / n for n in SP.SELECTION_INPUTS], [src, out]) as g:
        ver = verify_selection_inputs(disc)
        sensor_sha = verify_sensor()
        write_json(src / "nb1a-source-manifest.json", {
            "schema": "NB1b-source-manifest-v1", "truth": SP.TRUTH_DERIVED,
            "statement": "the accepted, frozen NB1a discovery products; read-only; never regenerated",
            "nb1a": {"branch": SP.NB1A_BRANCH, "accepted_commit": SP.NB1A_ACCEPTED_COMMIT,
                     "report_commit": SP.NB1A_REPORT_COMMIT, "discovery_frozen_at": SP.NB1A_FROZEN_AT,
                     "run": str(SP.NB1A_RUN)},
            "freeze_identity": {"path": str(disc / "bootstrap-freeze.json"),
                                "sha256": ver["hashes"]["bootstrap-freeze.json"]},
            "nb1a_frozen_files": ver["freeze"]["files"],
            "selection_inputs": {n: {"path": str(disc / n), "sha256": h, "verified": True} for n, h in ver["hashes"].items()},
            "sensor": {"path": str(SP.SENSOR_SOURCE), "sha256": sensor_sha, "git_blob": SP.SENSOR_SOURCE_BLOB,
                       "CORE_FOV_DEG": SP.CORE_FOV_DEG},
            "code": code})
        data = S.load_selection_inputs(disc)
        if len(data["hypotheses"]) != SP.NB1A_HYPOTHESES:
            raise SystemExit(f"{PREFIX} STOP NB1a hypothesis count {len(data['hypotheses'])} != {SP.NB1A_HYPOTHESES}")
        try:
            res = S.serviceability(data["labels"], data["hypotheses"])
        except S.PartitionInvariantError as exc:
            raise SystemExit(f"{PREFIX} STOP partition invariant violated: {exc}")
        write_selection(out, res)
        summ = S.summary(res, data["summary"]["hypotheses"])
        summ["seconds"] = round(time.perf_counter() - t0, 2)
        write_json(out / "selection-summary.json", summ)
    rec = g.record()
    rec["truth_firewall_violations"] = len(rec["violations"])
    write_json(out / "selection-opened-files.json", rec)
    if rec["violations"]:
        raise SystemExit(f"{PREFIX} STOP selection truth-firewall violations: {rec['violations']}")
    n = summ["counts"]
    print(f"{PREFIX} select: {summ['total_hypotheses']} hypotheses -> environment {n[SP.ENVIRONMENT]}, primary "
          f"{n[SP.PRIMARY]}, secondary {n[SP.SECONDARY]}, marginal {n[SP.MARGINAL]}, edge-only {n[SP.EDGE_ONLY]}; "
          f"guard data reads {len(rec['data_reads'])}, violations 0 ({summ['seconds']} s)")
    return summ


def freeze(run: Path) -> dict:
    sel = run / "selection"
    rec = {"schema": "NB1b-serviceability-freeze-v1", "truth": SP.TRUTH_DERIVED,
           "files": {n: sha256(sel / n) for n in FROZEN},
           "source_nb1a_freeze": read_json(run / "source/nb1a-source-manifest.json")["freeze_identity"],
           "sensor_constants": SP.SENSOR_CONSTANTS,
           "sensor_source": {"path": str(SP.SENSOR_SOURCE), "sha256": sha256(SP.SENSOR_SOURCE)},
           "selection_config": SP.SELECTION_CONFIG, "selection_config_sha256": config_sha256(),
           "selection_code": {n: sha256(p) for n, p in SELECTION_CODE.items()}, "code": code_state(),
           "frozen_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    write_json(sel / "serviceability-freeze.json", rec)
    print(f"{PREFIX} freeze: {len(rec['files'])} selection products hashed")
    return rec


def verify_freeze(run: Path) -> dict:
    sel = run / "selection"
    fz = read_json(sel / "serviceability-freeze.json")
    bad = [n for n, h in fz["files"].items() if sha256(sel / n) != h]
    if bad or set(fz["files"]) != set(FROZEN):
        raise SystemExit(f"{PREFIX} STOP frozen serviceability products do not verify: {bad}")
    return fz


# ------------------------------------------------------------------ path 2: reference / evaluation (section 12)
def composition(rows: list[tuple[int, float]], names: dict, total: float, top: int) -> dict:
    """Support-weighted reference composition of one hypothesis from its (o, sr) overlap rows."""
    rows = sorted(rows, key=lambda x: (-x[1], x[0]))
    o0 = math.fsum(sr for o, sr in rows if o == 0)
    cat = math.fsum(sr for o, sr in rows if o > 0)
    return {"authored_ids_intersected": sum(1 for o, _ in rows if o > 0), "reference_ids_intersected": len(rows),
            "O0_fraction": o0 / total, "catalog_fraction": cat / total,
            "dominant": {"o": rows[0][0], "name": names.get(rows[0][0], O0_NAME), "fraction": rows[0][1] / total} if rows else None,
            "composition": [{"o": o, "name": names.get(o, O0_NAME), "fraction": sr / total} for o, sr in rows[:top]]}


def footprint_reference(cells: np.ndarray, oid_flat: np.ndarray, names: dict) -> dict:
    o = oid_flat[cells]
    ids, cnt = np.unique(o, return_counts=True)
    order = sorted(zip(cnt.tolist(), ids.tolist()), key=lambda x: (-x[0], x[1]))
    return {"cells": int(len(cells)), "O0_cells": int((o == 0).sum()), "catalog_cells": int((o > 0).sum()),
            "ids": [{"o": int(i), "name": names.get(int(i), O0_NAME), "cells": int(c)} for c, i in order[:4]]}


def reference_summary(recs: list[dict], fp: dict, ov: dict, mat: dict, oid: np.ndarray, srgb8: np.ndarray,
                      fz: dict) -> dict:
    names = {int(r["o"]): r["name"] for r in ov["per_reference_id"] if int(r["o"]) > 0}
    rows_by = {}
    for h, o, sr in zip(mat["h"].tolist(), mat["o"].tolist(), mat["support_sr"].tolist()):
        rows_by.setdefault(int(h), []).append((int(o), float(sr)))
    oid_flat = oid.reshape(-1).astype(np.int64)
    rgb = srgb8.reshape(-1, 3).astype(np.float64)
    comp = {r["label"]: composition(rows_by.get(r["label"], []), names, r["support_sr"], 6) for r in recs}

    def fp_cells(kind, k):
        p = fp[f"{kind}_ptr"]
        return fp[f"{kind}_cells"][p[k]:p[k + 1]].astype(np.int64)

    cands = []
    for k, r in enumerate(recs):
        if r["class"] not in (SP.PRIMARY, SP.SECONDARY):
            continue
        cen = fp_cells("center", k)
        cands.append({"id": r["id"], "class": r["class"], "queue": r["queue"], **comp[r["label"]],
                      "full_footprint_reference": footprint_reference(fp_cells("full", k), oid_flat, names),
                      "rgb": {"center_footprint_mean_srgb8": [float(x) for x in rgb[cen].mean(axis=0)],
                              "center_footprint_cells": int(len(cen))}})
    cands.sort(key=lambda c: (c["queue"]["name"] != "primary", c["queue"]["rank"]))
    env = []
    for k, r in enumerate(recs):
        if r["class"] == SP.ENVIRONMENT:
            env.append({"id": r["id"], "support_sr": r["support_sr"], "fraction_of_4pi": r["fraction_of_4pi"],
                        **composition(rows_by.get(r["label"], []), names, r["support_sr"], 10),
                        "full_footprint_reference": footprint_reference(fp_cells("full", k), oid_flat, names)})
    per_class = {}
    for cls in SP.CLASSES:
        rs = [r for r in recs if r["class"] == cls]
        sup = math.fsum(r["support_sr"] for r in rs)
        by_o = {}
        for r in rs:
            for o, sr in rows_by.get(r["label"], []):
                by_o.setdefault(o, []).append(sr)
        tot = {o: math.fsum(v) for o, v in by_o.items()}
        top = sorted(((o, s) for o, s in tot.items() if o > 0), key=lambda x: (-x[1], x[0]))[:6]
        per_class[cls] = {
            "hypotheses": len(rs), "support_sr": sup,
            "O0_fraction": tot.get(0, 0.0) / sup if sup else None,
            "catalog_fraction": math.fsum(s for o, s in tot.items() if o > 0) / sup if sup else None,
            "hypotheses_dominated_by_O0": sum(1 for r in rs if comp[r["label"]]["dominant"]
                                              and comp[r["label"]]["dominant"]["o"] == 0),
            "hypotheses_touching_O0": sum(1 for r in rs if any(o == 0 for o, _ in rows_by.get(r["label"], []))),
            "top_authored_ids": [{"o": o, "name": names.get(o, ""), "support_sr": s, "fraction": s / sup} for o, s in top]}
    return {"schema": "NB1b-candidate-reference-summary-v1", "truth": SP.TRUTH_REFERENCE,
            "statement": "descriptive, post-freeze relation of the frozen serviceability classes to the NB1a reference "
                         "products and RGB proxy; not ground truth; no accuracy / precision / recall / IoU; changes no "
                         "category and no rank",
            "computed_after_freeze": True, "frozen_selection_sha256": fz["files"],
            "reference_inputs_sha256": dict(SP.EVALUATION_INPUTS),
            "candidates": cands, "environment": env, "per_class": per_class}


def evaluate(run: Path) -> dict:
    sel, out = run / "selection", run / "evaluation"
    out.mkdir(parents=True, exist_ok=True)
    refs = {n: SP.NB1A_RUN / n for n in SP.EVALUATION_INPUTS}
    frozen = [sel / n for n in FROZEN] + [sel / "serviceability-freeze.json"]
    with OpenGuard("evaluation", frozen + list(refs.values()), [out]) as g:
        fz = verify_freeze(run)
        g.mark("freeze_verified")
        recs = read_json(sel / "serviceability.json")["hypotheses"]
        with np.load(sel / "footprints.npz") as z:
            fp = {k: z[k] for k in z.files}
        g.mark("reference_access_begins")
        bad = [n for n, p in refs.items() if sha256(p) != SP.EVALUATION_INPUTS[n]]
        if bad:
            raise SystemExit(f"{PREFIX} STOP NB1a reference product hash mismatch: {bad}")
        ov = read_json(refs["evaluation/overlap-summary.json"])
        with np.load(refs["evaluation/overlap-matrix.npz"]) as z:
            mat = {k: z[k] for k in ("h", "o", "cells", "support_sr")}
        with np.load(refs["evaluation/reference-cells.npz"]) as z:
            oid = z["object_index"]
        with np.load(refs["input/rgb-sensory.npz"]) as z:
            srgb8 = z["srgb8"]
        summ = reference_summary(recs, fp, ov, mat, oid, srgb8, fz)
        write_json(out / "candidate-reference-summary.json", summ)
    rec = g.record()
    rec["ordered_data_events"] = [e.get("label") or e.get("path") for e in rec["events"]
                                  if e.get("event") == "mark" or e.get("kind") == "data-read"]
    write_json(out / "evaluation-opened-files.json", rec)
    after = verify_freeze(run)
    if rec["violations"]:
        raise SystemExit(f"{PREFIX} STOP evaluation guard violations: {rec['violations']}")
    print(f"{PREFIX} evaluate: {len(summ['candidates'])} queued candidates, {len(summ['environment'])} environment "
          f"candidate(s) described; frozen products re-verified ({len(after['files'])})")
    return summ


# ------------------------------------------------------------------ synthetic known answers (section 15)
def _synthetic_hyps(labels: np.ndarray, seeds: dict) -> list[dict]:
    """NB1a-like records: canonical support from the label rows, the given seed and a declared clearance."""
    yc, pc = A.yaw_centers_deg(), A.pitch_centers_deg()
    out = []
    for lab in sorted(seeds):
        row, col, clr = seeds[lab]
        rows = np.flatnonzero(labels.reshape(-1) == lab) // A.WIDTH
        sup = A.support_sr(np.bincount(rows, minlength=A.HEIGHT))
        out.append({"id": f"H{lab:04d}", "label": lab, "cells": int(len(rows)), "support_sr": sup,
                    "fraction_of_4pi": sup / (4 * math.pi), "range_m": {"min": 2.0, "median": 2.0, "max": 2.0},
                    "seed": {"row": row, "col": col, "yaw_deg": float(yc[col]), "pitch_deg": float(pc[row]),
                             "range_m": 2.0, "clearance_rad": clr, "fallback": None, "tied_candidates": 1}})
    return out


def synthetic_cases() -> list[tuple]:
    """(name, labels, seeds {label: (row, col, clearance)}, expected classes, extra predicate or 'raises')."""
    H, W = A.HEIGHT, A.WIDTH
    dirs = A.cell_directions_h().reshape(-1, 3)
    P, Sx, M, E, V = SP.PRIMARY, SP.SECONDARY, SP.MARGINAL, SP.EDGE_ONLY, SP.ENVIRONMENT

    def blank():
        return np.zeros((H, W), np.int64)

    def disk(lab, row, col, radius_deg, value):
        a = S.angular_distance(dirs[row * W + col], dirs).reshape(H, W)
        lab[a <= math.radians(radius_deg) + SP.ANGLE_EPS_RAD] = value
        return lab

    def fp_set(res, hid, kind="full"):
        k = [r["id"] for r in res["records"]].index(hid)
        return set(res["footprints"][f"{kind}_cells"][k].tolist())

    def rec(res, hid):
        return next(r for r in res["records"] if r["id"] == hid)

    cases = []
    sq = blank(); sq[160:201, 340:381] = 1
    cases.append(("FULL-safe square -> PRIMARY_LOOK", sq, {1: (180, 360, 0.17)}, {"H0001": P}, None))
    cases.append(("7-degree disk -> SECONDARY_LOOK", disk(blank(), 180, 360, 7.0, 1), {1: (180, 360, 0.12)},
                  {"H0001": Sx}, lambda r: rec(r, "H0001")["full"]["invalid_cells"] > 0))
    cases.append(("3-degree disk with positive clearance -> MARGINAL", disk(blank(), 180, 360, 3.0, 1),
                  {1: (180, 360, 0.05)}, {"H0001": M}, None))
    st = blank(); st[180, 300:421] = 1
    cases.append(("zero-clearance strip -> EDGE_ONLY", st, {1: (180, 360, 0.0)}, {"H0001": E}, None))
    hp = blank(); hp[0:181, :] = 1; hp[181:, :] = 2
    cases.append(("hemisphere plus one row -> ENVIRONMENT_CANDIDATE", hp, {1: (90, 360, 0.7), 2: (270, 360, 0.7)},
                  {"H0001": V, "H0002": P}, lambda r: rec(r, "H0001")["support_sr"] > 2 * math.pi))
    hm = blank(); hm[0:179, :] = 1; hm[179:, :] = 2
    cases.append(("hemisphere minus one row -> not environment", hm, {1: (90, 360, 0.7), 2: (270, 360, 0.7)},
                  {"H0001": P, "H0002": V}, lambda r: rec(r, "H0001")["support_sr"] < 2 * math.pi))
    ih = sq.copy(); ih[172, 360] = 0
    cases.append(("invalid cell inside the footprint -> unsafe", ih, {1: (180, 360, 0.06)}, {"H0001": M},
                  lambda r: rec(r, "H0001")["center"]["invalid_cells"] == 1 and rec(r, "H0001")["center"]["other_cells"] == 0))
    oh = sq.copy(); oh[172, 360] = 2
    cases.append(("other-hypothesis cell inside the footprint -> unsafe", oh, {1: (180, 360, 0.06), 2: (172, 360, 0.0)},
                  {"H0001": M, "H0002": E},
                  lambda r: rec(r, "H0001")["center"]["other_cells"] == 1 and rec(r, "H0001")["center"]["invalid_cells"] == 0))
    sm = blank(); sm[160:201, 700:720] = 1; sm[160:201, 0:21] = 1

    def seam_shift(res):
        inner = S.serviceability(sq, _synthetic_hyps(sq, {1: (180, 360, 0.17)}))
        shifted = {(c // W) * W + (c % W - 360) % W for c in fp_set(inner, "H0001")}
        got = fp_set(res, "H0001")
        return got == shifted and any(c % W >= 700 for c in got) and any(c % W <= 20 for c in got)
    cases.append(("footprint across the longitude seam (yaw-shift of the interior footprint)", sm, {1: (180, 0, 0.17)},
                  {"H0001": P}, seam_shift))
    sh = sm.copy(); sh[180, 714] = 0
    cases.append(("no-geometry cell across the seam -> unsafe", sh, {1: (180, 0, 0.05)}, {"H0001": M},
                  lambda r: rec(r, "H0001")["center"]["invalid_cells"] == 1))
    cap = blank(); cap[0:31, :] = 1
    cases.append(("near-pole footprint crossing the pole -> PRIMARY_LOOK", cap, {1: (3, 100, 0.2)}, {"H0001": P},
                  lambda r: 0 * W + 460 in fp_set(r, "H0001")))
    cap2 = blank(); cap2[0:18, :] = 1
    cases.append(("near-pole small cap -> SECONDARY_LOOK", cap2, {1: (3, 100, 0.1)}, {"H0001": Sx}, None))
    tie = disk(blank(), 180, 360, 7.0, 1); tie[168, 360] = 0
    cases.append(("exact 6-degree tie on the meridian -> CENTER unsafe", tie, {1: (180, 360, 0.1)}, {"H0001": M},
                  lambda r: rec(r, "H0001")["center"]["invalid_cells"] == 1
                  and rec(r, "H0001")["center"]["boundary_tie_cells"] >= 1))
    t65 = disk(blank(), 180, 360, 7.0, 1); t65[167, 360] = 0
    cases.append(("the same cell at 6.5 degrees -> CENTER safe", t65, {1: (180, 360, 0.1)}, {"H0001": Sx}, None))

    def ring_cells(lo_deg, hi_deg):   # grid cells strictly between two radii around (180, 360)
        a = S.angular_distance(dirs[180 * W + 360], dirs)
        return int(((a > math.radians(lo_deg) + SP.ANGLE_EPS_RAD) & (a <= math.radians(hi_deg))).sum())
    cases.append(("disk of exactly R_FULL -> PRIMARY_LOOK (tight; cells lie between R_FULL and sqrt(2) 6 deg)",
                  disk(blank(), 180, 360, SP.R_FULL_DEG, 1), {1: (180, 360, 0.14)}, {"H0001": P},
                  lambda r: ring_cells(SP.R_FULL_DEG, math.sqrt(2) * 6.0) > 0))
    cases.append(("disk of exactly R_CENTER -> SECONDARY_LOOK (tight; cells lie between 6 and 6.5 deg)",
                  disk(blank(), 180, 360, SP.R_CENTER_DEG, 1), {1: (180, 360, 0.1)}, {"H0001": Sx},
                  lambda r: ring_cells(6.0, 6.5) > 0))
    cases.append(("partition invariant: zero clearance with a SAFE CENTER -> STOP", sq, {1: (180, 360, 0.0)}, {},
                  "raises"))
    return cases


def synthetic_results(**variant) -> list[dict]:
    """Run every known-answer case; ``variant`` (serviceability keywords) exists only for the mutation suite."""
    results = []
    for name, labels, seeds, want, extra in synthetic_cases():
        hyps = _synthetic_hyps(labels, seeds)
        if extra == "raises":
            try:
                S.serviceability(labels, hyps, **variant)
                got, ok = {"raised": False}, False
            except S.PartitionInvariantError as exc:
                got, ok = {"raised": True, "message": str(exc)}, True
        else:
            try:
                res = S.serviceability(labels, hyps, **variant)
            except S.PartitionInvariantError as exc:
                results.append({"name": name, "expected": want, "got": {"raised": str(exc)}, "ok": False})
                continue
            got = {r["id"]: r["class"] for r in res["records"]}
            ok = got == want and (extra is None or bool(extra(res)))
            got = {"classes": got, "center_safe": {r["id"]: r["center"]["safe"] for r in res["records"]},
                   "full_safe": {r["id"]: r["full"]["safe"] for r in res["records"]}}
        results.append({"name": name, "expected": want if extra != "raises" else {"raises": "PartitionInvariantError"},
                        "got": got, "ok": bool(ok)})
    return results


def synthetic(run: Path) -> dict:
    out = run / "synthetic"
    out.mkdir(parents=True, exist_ok=True)
    results = synthetic_results()
    for x in results:
        print(f"{PREFIX} synthetic {'PASS' if x['ok'] else 'FAIL'} {x['name']}")
    report = {"schema": "NB1b-synthetic-report-v1", "code": code_state(), "sensor": SP.SENSOR_CONSTANTS,
              "cases": results, "passed": all(x["ok"] for x in results),
              "note": "known-answer label rasters and seeds; no Blender, no Classroom"}
    write_json(out / "synthetic-report.json", report)
    print(f"{PREFIX} synthetic {sum(x['ok'] for x in results)}/{len(results)} "
          f"{'NB1B_SYNTHETIC_PASS' if report['passed'] else 'FAILED'}")
    return report


# ------------------------------------------------------------------ manifest
def write_manifest(run: Path) -> dict:
    files = sorted(str(p.relative_to(run)) for p in run.rglob("*") if p.is_file()
                   and p.name not in ("manifest.json", "check-summary.json", "process-log.jsonl"))
    m = {"schema": "NB1b-manifest-v1", "experiment": "Natural Bootstrap-1b: Foveal Serviceability",
         "contract": "docs/natural-bootstrap/nb1b-foveal-serviceability-contract.md", "code": code_state(),
         "base_commit": SP.BASE_COMMIT, "nb1a_run": str(SP.NB1A_RUN),
         "selection_inputs": {n: {"path": str(SP.NB1A_RUN / "discovery" / n), "sha256": h} for n, h in SP.SELECTION_INPUTS.items()},
         "evaluation_inputs": {n: {"path": str(SP.NB1A_RUN / n), "sha256": h} for n, h in SP.EVALUATION_INPUTS.items()},
         "sensor_source": {"path": str(SP.SENSOR_SOURCE), "sha256": SP.SENSOR_SOURCE_SHA256},
         "truth": {"source/": SP.TRUTH_DERIVED, "selection/": SP.TRUTH_DERIVED, "evaluation/": SP.TRUTH_REFERENCE},
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
            import nb1b_visuals
            nb1b_visuals.visualize(run, a.visuals.resolve())
            write_manifest(run)
        status = "ok"
        return 0
    finally:
        log_process(run, a.cmd, t0, status)


if __name__ == "__main__":
    raise SystemExit(main())
