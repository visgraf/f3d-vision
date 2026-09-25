#!/usr/bin/env python3
"""Golden behavior comparator for Classroom-Oracle-1 runs.

Promoted from the Consolidation-1/2 scratch comparator (the one that established
0 behavioral mismatches between the legacy, Consolidation-1 and Consolidation-2 full
runs), with the same acceptance semantics, now expressed as one extraction plus one
diff so that a run can be compared with another run or with a committed signature.

    # run vs run (either side may also be a signature .json)
    .venv/bin/python tools/compare_golden.py compare REFERENCE CANDIDATE
    # write a compact signature of an accepted run
    .venv/bin/python tools/compare_golden.py signature RUN --out tests/golden/classroom-oracle1-signature.json
    # fail-capable in-memory checks of the comparator itself
    .venv/bin/python tools/compare_golden.py self-test

Behavior (compared exactly):
  seeds.json (instances with seed gazes, controller domain, scan step, head pose);
  instance_catalog.json; the dense evaluation-only reachable samples;
  manifest fields (digest, spec, profile, device, smoke, counts, control_complete,
  terminations, truth isolation, fg/bg decomposition, truth scope, smoke gate,
  spp override, scene); target order; per object: name, seed gaze, fixation count,
  termination, final surfels, incidental ids, final map arrays; per look: gaze,
  action source, target/valid points, map sizes, new/non-new surfels, matcher, fusion,
  FSG6f decision, Cyclopean decision, calibration, map-snapshot arrays, oracle-patch
  arrays, observation Object Index and Position arrays; evaluation.json counts,
  coverage and per-object table when the reference has an evaluation.

Excluded, by design:
  RGB content -- map/final-map ``rgb`` and observation ``rgb_L``/``rgb_R``.  The OptiX
  Combined pass is not bit-reproducible run to run with fixed seeds and spp
  (docs/baseline-contract.md); only its key, dtype and shape are compared.  In
  run-vs-run mode the RGB differences are measured and reported, never judged.
  Unstable metadata -- acquisition.json (timestamps, render seconds), logs, EXR and
  PNG bytes, stored relative artifact paths, .npz archive bytes.

Array equality is np.array_equal(equal_nan=True) plus equal dtype and shape, realized
as a sha256 over dtype, shape and canonical little-endian C-order bytes in which every
NaN is the canonical NaN and -0.0 is +0.0.  JSON dicts too large to keep verbatim are
compared by sha256 of their canonical JSON (sorted keys, shortest-repr floats).
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np

SCHEMA = "fov3d-golden-signature-v1"
RGB_MAP_KEYS = frozenset({"rgb"})            # map snapshots and final maps
RGB_OBS_PREFIX = "rgb_"                      # oracle_observation.npz: rgb_L, rgb_R
MANIFEST_FIELDS = (
    "public_digest", "spec_id", "profile", "device", "smoke", "oracle_visible_instance_count",
    "attempted_instance_count", "control_complete", "total_fixations", "termination_counts",
    "dense_evaluation_truth_opened_during_control", "foreground_background_decomposition",
    "controller_truth_scope", "smoke_gate", "spp_override", "scene",
)
SEED_FIELDS = ("instances", "controller_domain_deg", "seed_scan_step_deg", "head_origin_w_m", "head_R_wh")
OBJECT_FIELDS = ("object_name", "seed_gaze_deg", "fixation_count", "termination", "final_map_surfels",
                 "incidental_instance_ids")
LOOK_FIELDS = ("step", "gaze_deg", "action_source", "target_points", "oracle_valid_points_all_instances",
               "map_size_before", "map_size_after", "new_surfels", "nonnew_target_points")
LOOK_DICTS = ("matcher", "fusion", "fsg6f_decision", "cyclopean_decision")
EVAL_FIELDS = ("reachable_samples_total", "covered_samples_total", "coverage_fraction_micro", "total_fixations",
               "zero_new_surfel_looks", "termination_counts", "oracle_visible_instances", "attempted_instances",
               "unexpected_attempted_instance_ids", "objects")
EXCLUDED = {
    "rgb_content": "map/final-map 'rgb' and observation 'rgb_L'/'rgb_R': OptiX Combined pass is not "
                   "bit-reproducible; key, dtype and shape are still compared",
    "unstable_metadata": "acquisition.json, logs, raw EXR bytes, benchmark PNGs, stored artifact paths, "
                         ".npz archive bytes, trajectory.partial.json (duplicate of the trajectory)",
}


# ---------------------------------------------------------------- canonical forms

def canonical_json(x: Any) -> str:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=True)


def json_sha256(x: Any) -> str:
    return hashlib.sha256(canonical_json(x).encode()).hexdigest()


def array_signature(a: np.ndarray) -> str:
    """'<dtype>[shape]:sha256' of canonical bytes; equal iff array_equal(equal_nan=True), same dtype/shape."""
    a = np.asarray(a)
    dt = a.dtype.newbyteorder("<") if a.dtype.byteorder == ">" else a.dtype
    b = np.ascontiguousarray(a, dtype=dt)
    if b.dtype.kind in "fc":
        b = np.where(np.isnan(b), np.array(np.nan, dtype=b.dtype), b) + np.array(0, dtype=b.dtype)
        b = np.ascontiguousarray(b, dtype=dt)
    shape = ",".join(map(str, a.shape))
    h = hashlib.sha256(f"{dt.str}[{shape}]".encode())
    h.update(b.tobytes())
    return f"{dt.str}[{shape}]:{h.hexdigest()}"


def excluded_signature(a: np.ndarray) -> str:
    return f"{np.asarray(a).dtype.str}[{','.join(map(str, np.shape(a)))}]:excluded-rgb"


def npz_signature(path: Path, rgb_key) -> dict[str, str] | None:
    """Per-key array signatures; RGB keys keep dtype/shape only.  None when the file is absent."""
    if not path.exists():
        return None
    with np.load(path, allow_pickle=False) as z:
        return {k: (excluded_signature(z[k]) if rgb_key(k) else array_signature(z[k])) for k in sorted(z.files)}


def dict_record(x: Any) -> Any:
    """Large per-look dicts: canonical hash plus top-level scalars for readable diffs."""
    if x is None:
        return None
    summary = {}
    if isinstance(x, dict):
        for k, v in sorted(x.items()):
            if v is None or isinstance(v, (bool, int, float, str)):
                summary[k] = v
            elif isinstance(v, list) and len(v) <= 3 and all(isinstance(e, (int, float)) for e in v):
                summary[k] = v
    return {"sha256": json_sha256(x), "summary": summary}


# ---------------------------------------------------------------- extraction

def _json(path: Path) -> Any:
    return json.loads(path.read_text()) if path.exists() else {"__absent__": str(path.name)}


def extract(run: Path) -> dict:
    """Everything the accepted comparator judges, as a JSON-able behavior record."""
    run = Path(run)
    manifest = _json(run / "manifest.json")
    seeds = _json(run / "bootstrap/seeds.json")
    catalog = _json(run / "bootstrap/instance_catalog.json")
    behavior: dict[str, Any] = {
        "seeds": {k: seeds.get(k) for k in SEED_FIELDS},
        "instance_catalog_sha256": json_sha256(catalog),
        "reachable_samples": npz_signature(run / "bootstrap/evaluation_only/reachable_samples.npz", lambda k: False),
        "manifest": {k: manifest.get(k) for k in MANIFEST_FIELDS},
        "target_ids": [o["instance_id"] for o in manifest.get("objects", [])],
        "objects": [],
    }
    for o in manifest.get("objects", []):
        iid = int(o["instance_id"])
        odir = run / "objects" / f"instance_{iid:04d}"
        rec = {"instance_id": iid, **{k: o.get(k) for k in OBJECT_FIELDS},
               "final_map": npz_signature(odir / "final_map.npz", lambda k: k in RGB_MAP_KEYS), "looks": []}
        for t in o.get("trajectory", []):
            s = int(t["step"])
            adir = odir / "acquisitions" / f"fix_{s:02d}"
            look = {k: t.get(k) for k in LOOK_FIELDS}
            look.update({k: dict_record(t.get(k)) for k in LOOK_DICTS})
            look["calibration_sha256"] = json_sha256(_json(adir / "calibration.json"))
            look["map"] = npz_signature(odir / "maps" / f"fix_{s:02d}.npz", lambda k: k in RGB_MAP_KEYS)
            look["patch"] = npz_signature(odir / "patches" / f"fix_{s:02d}.npz", lambda k: k in RGB_MAP_KEYS)
            look["observation"] = npz_signature(adir / "oracle_observation.npz", lambda k: k.startswith(RGB_OBS_PREFIX))
            rec["looks"].append(look)
        behavior["objects"].append(rec)
    ev_path = run / "evaluation.json"
    behavior["evaluation"] = ({k: v for k, v in _json(ev_path).items() if k in EVAL_FIELDS}
                              if ev_path.exists() else None)
    behavior["headline"] = headline(behavior)
    return behavior


def headline(b: dict) -> dict:
    looks = [lk for o in b["objects"] for lk in o["looks"]]
    terms = Counter(str(o["termination"]) for o in b["objects"])
    ev = b.get("evaluation") or {}
    m = b["manifest"]
    return {
        "targets": len(b["target_ids"]),
        "fixations": len(looks),
        "action_sources": dict(sorted(Counter(str(lk["action_source"]) for lk in looks).items())),
        "terminations": dict(sorted(terms.items())),
        "attention_complete": terms.get("attention_complete", 0),
        "watchdog_24": terms.get("watchdog_24", 0),
        "reachable": ev.get("reachable_samples_total"),
        "covered": ev.get("covered_samples_total"),
        "coverage": ev.get("coverage_fraction_micro"),
        "zero_new_surfel_looks": ev.get("zero_new_surfel_looks"),
        "truth_opened_during_control": m.get("dense_evaluation_truth_opened_during_control"),
        "foreground_background_decomposition": m.get("foreground_background_decomposition"),
        "control_complete": m.get("control_complete"),
    }


# ---------------------------------------------------------------- comparison

def diff(ref: Any, cand: Any, path: str = "", out: list[str] | None = None) -> list[str]:
    """Exact structural diff of two behavior records; every difference is one line."""
    out = [] if out is None else out
    if isinstance(ref, dict) and isinstance(cand, dict):
        for k in sorted(set(ref) | set(cand), key=str):
            if k not in cand:
                out.append(f"{path}.{k}: missing in candidate")
            elif k not in ref:
                out.append(f"{path}.{k}: unexpected in candidate")
            else:
                diff(ref[k], cand[k], f"{path}.{k}", out)
    elif isinstance(ref, list) and isinstance(cand, list):
        if len(ref) != len(cand):
            out.append(f"{path}: length {len(ref)} != {len(cand)}")
        for i, (a, b) in enumerate(zip(ref, cand)):
            label = i
            if isinstance(a, dict) and "instance_id" in a:
                label = f"{i}:instance_{a['instance_id']}"
            elif isinstance(a, dict) and "step" in a:
                label = f"{i}:step_{a['step']}"
            diff(a, b, f"{path}[{label}]", out)
    elif canonical_json(ref) != canonical_json(cand):
        out.append(f"{path}: reference={_short(ref)} candidate={_short(cand)}")
    return out


def _short(x: Any, n: int = 120) -> str:
    s = canonical_json(x)
    return s if len(s) <= n else s[:n] + "..."


def rgb_report(ref_run: Path, cand_run: Path, behavior: dict) -> dict:
    """Informational only: measured RGB differences between two run directories."""
    map_dev: list[float] = []
    obs_dev: list[float] = []
    obs_neq: list[float] = []
    for o in behavior["objects"]:
        od = f"objects/instance_{o['instance_id']:04d}"
        paths = [f"{od}/maps/fix_{lk['step']:02d}.npz" for lk in o["looks"]] + [f"{od}/final_map.npz"]
        for p in paths:
            a, b = ref_run / p, cand_run / p
            if a.exists() and b.exists():
                with np.load(a) as za, np.load(b) as zb:
                    for k in RGB_MAP_KEYS & set(za.files) & set(zb.files):
                        if za[k].shape == zb[k].shape and za[k].size:
                            map_dev.append(float(np.abs(za[k].astype(float) - zb[k].astype(float)).max()))
        for lk in o["looks"]:
            p = f"{od}/acquisitions/fix_{lk['step']:02d}/oracle_observation.npz"
            a, b = ref_run / p, cand_run / p
            if a.exists() and b.exists():
                with np.load(a) as za, np.load(b) as zb:
                    for k in [k for k in za.files if k.startswith(RGB_OBS_PREFIX) and k in zb.files]:
                        if za[k].shape == zb[k].shape:
                            obs_dev.append(float(np.abs(za[k].astype(float) - zb[k].astype(float)).max()))
                            obs_neq.append(float((za[k] != zb[k]).mean()))
    return {
        "map_rgb_arrays": len(map_dev),
        "map_rgb_max_abs_dev": max(map_dev) if map_dev else 0.0,
        "observation_rgb_arrays": len(obs_dev),
        "observation_rgb_max_abs_dev": max(obs_dev) if obs_dev else 0.0,
        "observation_rgb_median_per_image_max_abs_dev": float(np.median(obs_dev)) if obs_dev else 0.0,
        "observation_rgb_mean_fraction_pixels_differing": float(np.mean(obs_neq)) if obs_neq else 0.0,
    }


def load_side(p: Path) -> tuple[dict, dict | None]:
    """A run directory or a signature file -> (behavior, meta or None)."""
    p = Path(p)
    if p.is_file():
        doc = json.loads(p.read_text())
        if doc.get("schema") != SCHEMA:
            raise SystemExit(f"{p}: not a {SCHEMA} signature")
        return doc["behavior"], doc.get("meta")
    if not (p / "manifest.json").exists():
        raise SystemExit(f"{p}: neither a run directory (no manifest.json) nor a signature file")
    return extract(p), None


def compare(reference: Path, candidate: Path, max_report: int = 60) -> int:
    ref, ref_meta = load_side(reference)
    cand, _ = load_side(candidate)
    if ref.get("evaluation") is not None and cand.get("evaluation") is None:
        print("[compare-golden] NOTE reference has an evaluation and the candidate has none; run the evaluator first")
    mismatches = diff(ref, cand, "behavior")
    counts = {
        "targets": len(cand["target_ids"]),
        "looks": sum(len(o["looks"]) for o in cand["objects"]),
        "npz_arrays_compared": sum(
            sum(1 for v in (lk[x] or {}).values() if not v.endswith(":excluded-rgb"))
            for o in cand["objects"] for lk in o["looks"] for x in ("map", "patch", "observation"))
            + sum(1 for o in cand["objects"] for v in (o["final_map"] or {}).values() if not v.endswith(":excluded-rgb")),
        "rgb_arrays_excluded": sum(
            sum(1 for v in (lk[x] or {}).values() if v.endswith(":excluded-rgb"))
            for o in cand["objects"] for lk in o["looks"] for x in ("map", "observation"))
            + sum(1 for o in cand["objects"] for v in (o["final_map"] or {}).values() if v.endswith(":excluded-rgb")),
    }
    print("[compare-golden] reference", reference, f"(signature from {ref_meta['generated_from']})" if ref_meta else "(run)")
    print("[compare-golden] candidate", candidate)
    print("[compare-golden] compared", json.dumps(counts, sort_keys=True))
    print("[compare-golden] headline", json.dumps(cand["headline"], sort_keys=True))
    if Path(reference).is_dir() and Path(candidate).is_dir():
        print("[compare-golden] rgb (informational, excluded)", json.dumps(rgb_report(Path(reference), Path(candidate), cand), sort_keys=True))
    for m in mismatches[:max_report]:
        print("[compare-golden] MISMATCH", m)
    if len(mismatches) > max_report:
        print(f"[compare-golden] ... {len(mismatches) - max_report} more")
    print(f"[compare-golden] MISMATCHES {len(mismatches)}")
    return 1 if mismatches else 0


def write_signature(run: Path, out: Path, label: str | None) -> int:
    behavior = extract(run)
    doc = {
        "schema": SCHEMA,
        "meta": {
            "generated_by": "tools/compare_golden.py signature",
            "generated_from": label or str(run),
            "compared_exactly": __doc__.split("Behavior (compared exactly):", 1)[1].split("Excluded, by design:", 1)[0].strip(),
            "excluded": EXCLUDED,
            "array_rule": "'<dtype>[shape]:sha256' over dtype, shape and canonical little-endian C-order bytes "
                          "(NaN canonical, -0.0 -> +0.0) == np.array_equal(equal_nan=True) with equal dtype/shape",
            "dict_rule": "sha256 of canonical JSON (sorted keys, compact separators, shortest-repr floats); "
                         "'summary' repeats top-level scalars for readable diffs",
        },
        "behavior": behavior,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")
    print(f"[compare-golden] signature {out} bytes={out.stat().st_size} headline={json.dumps(behavior['headline'], sort_keys=True)}")
    return 0


# ---------------------------------------------------------------- self-test

def self_test() -> list[str]:
    fails: list[str] = []
    a = np.array([0.0, 1.5, np.nan], np.float32)
    if array_signature(a) != array_signature(np.array([-0.0, 1.5, np.nan], np.float32)):
        fails.append("-0.0 and +0.0 must compare equal (array_equal semantics)")
    odd_nan = np.array([0.0, 1.5, 0.0], np.float32); odd_nan.view(np.uint32)[2] = 0x7FC00001
    if array_signature(a) != array_signature(odd_nan):
        fails.append("NaN payloads must compare equal (equal_nan=True)")
    if array_signature(a) == array_signature(np.array([0.0, 1.5000001, np.nan], np.float32)):
        fails.append("one changed float element not detected")
    if array_signature(a) == array_signature(a.astype(np.float64)):
        fails.append("dtype change not detected")
    if array_signature(np.zeros((2, 3), np.int32)) == array_signature(np.zeros((3, 2), np.int32)):
        fails.append("shape change not detected")
    if array_signature(np.arange(4, dtype=">i4")) != array_signature(np.arange(4, dtype="<i4")):
        fails.append("byte order must not matter")
    base = {"objects": [{"instance_id": 7, "looks": [{"step": 0, "gaze_deg": [1.0, 2.0], "action_source": "fsg6f",
                                                      "map": {"rgb": "<f4[3,3]:excluded-rgb", "xyz_h": "<f4[3,3]:aa"}}]}],
            "headline": {"coverage": 0.8746927069106801}}
    same = json.loads(json.dumps(base))
    if diff(base, same):
        fails.append("identical records reported different")
    for mutate, label in (
        (lambda d: d["objects"][0]["looks"][0]["gaze_deg"].__setitem__(1, 2.0000001), "gaze"),
        (lambda d: d["objects"][0]["looks"][0].__setitem__("action_source", "cyclopean_epistemic"), "action source"),
        (lambda d: d["objects"][0]["looks"][0]["map"].__setitem__("xyz_h", "<f4[3,3]:bb"), "map array"),
        (lambda d: d["headline"].__setitem__("coverage", 0.8746927069106802), "coverage last digit"),
        (lambda d: d["objects"][0]["looks"].append({"step": 1}), "extra look"),
        (lambda d: d["objects"][0]["looks"][0]["map"].__setitem__("rgb", "<f8[3,3]:excluded-rgb"), "rgb dtype"),
    ):
        d = json.loads(json.dumps(base)); mutate(d)
        if not diff(base, d):
            fails.append(f"mutation not detected: {label}")
    return fails


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("compare", help="compare a candidate run (or signature) with a reference run (or signature)")
    c.add_argument("reference", type=Path)
    c.add_argument("candidate", type=Path)
    c.add_argument("--max-report", type=int, default=60)
    s = sub.add_parser("signature", help="write the compact behavior signature of an accepted run")
    s.add_argument("run", type=Path)
    s.add_argument("--out", type=Path, required=True)
    s.add_argument("--label", default=None, help="provenance text recorded as meta.generated_from")
    sub.add_parser("self-test", help="in-memory checks that the comparator detects what it must")
    args = ap.parse_args()
    if args.cmd == "compare":
        return compare(args.reference, args.candidate, args.max_report)
    if args.cmd == "signature":
        return write_signature(args.run, args.out, args.label)
    bad = self_test()
    for b in bad:
        print("[compare-golden] SELF-TEST FAIL", b)
    print("[compare-golden] self-test", "FAILED" if bad else "PASS")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
