"""Greedy Foveal Explorer, official baseline: the equivalence checker (Engineering-1).

Contract: docs/engineering/greedy-foveal-playground-baseline-contract.md, section 7.

    .venv/bin/python tools/greedy_foveal/check_equivalence.py source
    .venv/bin/python tools/greedy_foveal/check_equivalence.py run --run RUN --baseline BASE [--prefix] [--known-answer]
    .venv/bin/python tools/greedy_foveal/check_equivalence.py selftest

``source``: each promoted file is executable-equal to its frozen tag blob (ASTs compared with docstrings removed), and
the host-side import closure of the official code loads only tracked modules, none of the NS1e lineage.
``run``: the scientific payload of RUN equals BASE.  Control-path products are compared bitwise; RGB (not reproducible
run to run under Cycles OPTIX, and never a control input) is reported, not compared; branch / commit / time metadata is
ignored.  ``--prefix`` compares a shorter run with the first N fixations of BASE; ``--known-answer`` also asserts the
literal frozen grow600 numbers.  ``selftest``: in-memory controls showing that every comparator can fail.

Exit status 0 on PASS, 1 on FAIL.  ``run`` writes its record next to RUN's products (``--out`` overrides).
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PREFIX = "[gfe-equiv]"

IMPL_TAG, IMPL_SHA = "greedy-foveal-explorer-v0-impl", "a437df048b555d5b59f6855b6572eea2665ab0da"
DEMO_TAG, DEMO_SHA = "greedy-foveal-explorer-v0-demo", "8066a246bf251fb1e2d66b7061899c32df236bf1"
SOURCES = {"explorer.py": IMPL_TAG, "run.py": IMPL_TAG, "render_server.py": IMPL_TAG,
           "visuals.py": DEMO_TAG, "demo.py": DEMO_TAG}
TAG_SHA = {IMPL_TAG: IMPL_SHA, DEMO_TAG: DEMO_SHA}

# trajectory.json: run-level fields compared exactly (everything else is metadata: code, timings)
SUMMARY_EXACT = ("schema", "label", "spp", "max_fix", "stop_reason", "fixations", "local_saccades", "global_saccades",
                 "final_seen_fraction", "final_depth_fraction", "final_surfels", "monotone_cells", "server_exit",
                 "head_pose_source", "parameters", "server")
SUMMARY_PREFIX = ("schema", "label", "spp", "monotone_cells", "server_exit", "head_pose_source", "parameters", "server")
ENTRY_METADATA = ("seconds", "render_seconds_lr")             # per-fixation wall-clock timings
POINTS_BITWISE = ("xyz_h", "instance_id_oracle", "err_mm")
POLICY_BITWISE = ("state", "core_valid", "gaze", "visited")
COVERAGE_BITWISE = ("state", "seen_history", "depth_history", "row_weights")
MAP_BITWISE = ("xyz_h", "instance_id_oracle", "support_count", "first_fixation", "patch_ids", "radius_cell_m")
EVAL_EXACT = ("schema", "label", "radius_m", "coverage_function", "vectorized_cross_check_agrees", "reference",
              "primary_all_geometry", "secondary_authored_index_gt_0", "instance0_noncatalog",
              "covered_cells_nn_distance_mm")
EVAL_EXPLORER_METADATA = ("wall_seconds", "seconds_sum")
EVAL_NPZ_BITWISE = ("cells_rc", "covered", "instance")
KNOWN_ANSWER = {"fixations": 542, "stop_reason": "seen >= 99 % of 4 pi", "local_saccades": 322, "global_saccades": 219,
                "seen_pct": "99.00", "depth_pct": "98.28", "covered_cells": 251966, "reference_cells": 255758,
                "cell_pct": "98.52", "solid_angle_pct": "98.32"}
MAX_LISTED = 10


# ------------------------------------------------------------------ small utilities
def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path: Path):
    return json.loads(Path(path).read_text())


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout


class Ledger:
    """Named pass / fail results plus reported (non-gating) observations."""

    def __init__(self) -> None:
        self.results: dict[str, dict] = {}
        self.reported: dict[str, object] = {}

    def check(self, name: str, ok: bool, detail=None) -> bool:
        self.results[name] = {"pass": bool(ok), **({} if detail is None else {"detail": detail})}
        return bool(ok)

    def report(self, name: str, value) -> None:
        self.reported[name] = value

    @property
    def all_pass(self) -> bool:
        return bool(self.results) and all(r["pass"] for r in self.results.values())

    def failures(self) -> list[str]:
        return [k for k, r in self.results.items() if not r["pass"]]


# ------------------------------------------------------------------ comparators (shared by run and selftest)
def executable_dump(source: str) -> str:
    """The AST of ``source`` with module / class / function docstrings removed (comments are not in the AST)."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                node.body = body[1:] or [ast.Pass()]
    return ast.dump(tree, include_attributes=False)


def bitwise_equal(a: np.ndarray, b: np.ndarray) -> bool:
    """Same dtype, same shape, same bytes (NaN-safe; distinguishes -0.0 from +0.0)."""
    a, b = np.asarray(a), np.asarray(b)
    return a.dtype == b.dtype and a.shape == b.shape and np.ascontiguousarray(a).tobytes() == \
        np.ascontiguousarray(b).tobytes()


def entry_differences(r: dict, b: dict, ignore: tuple[str, ...]) -> list[str]:
    """Keys of one trajectory entry whose JSON values differ (floats compare exactly; JSON keeps repr precision)."""
    keys = (set(r) | set(b)) - set(ignore)
    return sorted(k for k in keys if r.get(k, KeyError) != b.get(k, KeyError))


def rgb_difference(a: np.ndarray, b: np.ndarray) -> dict:
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    if a.shape != b.shape:
        return {"same_shape": False, "shape_run": list(a.shape), "shape_baseline": list(b.shape)}
    d = np.abs(a - b)
    return {"same_shape": True, "values": int(d.size), "differing": int((d > 0).sum()),
            "max_abs": float(d.max()) if d.size else 0.0, "mean_abs": float(d.mean()) if d.size else 0.0}


def npz_payload(path: Path, keys: tuple[str, ...]) -> dict:
    with np.load(path, allow_pickle=False) as z:
        return {k: np.array(z[k]) for k in z.files if k in keys or k == "rgb"} | {"_keys": sorted(z.files)}


def ply_split(path: Path) -> tuple[bytes, np.ndarray]:
    data = Path(path).read_bytes()
    end = data.index(b"end_header\n") + len(b"end_header\n")
    rec = np.frombuffer(data[end:], dtype=[("x", "<f4"), ("y", "<f4"), ("z", "<f4"),
                                           ("r", "u1"), ("g", "u1"), ("b", "u1")])
    return data[:end], rec


def merge_rgb(acc: dict, d: dict) -> None:
    if not d.get("same_shape", False):
        acc["shape_mismatches"] = acc.get("shape_mismatches", 0) + 1
        return
    acc["values"] = acc.get("values", 0) + d["values"]
    acc["differing"] = acc.get("differing", 0) + d["differing"]
    acc["max_abs"] = max(acc.get("max_abs", 0.0), d["max_abs"])


# ------------------------------------------------------------------ source mode
def host_import_closure() -> dict:
    """Import the official host modules in a fresh interpreter; list the repository files that were loaded."""
    code = (
        "import json, os, sys\n"
        "sys.dont_write_bytecode = True\n"
        f"sys.path.insert(0, {str(HERE)!r})\n"
        "import explorer, run, visuals, demo\n"
        "import breadth1_glance, breadth1_spec, classroom_oracle1_eval, fsg3_surface_map\n"
        f"root = {str(REPO)!r} + '/'\n"
        "files = sorted({os.path.relpath(os.path.realpath(m.__file__), root) for m in list(sys.modules.values())\n"
        "                if getattr(m, '__file__', None) and os.path.realpath(m.__file__).startswith(root)})\n"
        "print(json.dumps(files))\n")
    out = subprocess.run([sys.executable, "-c", code], cwd=REPO, capture_output=True, text=True)
    if out.returncode != 0:
        return {"ok": False, "error": out.stderr[-2000:]}
    files = json.loads(out.stdout.strip().splitlines()[-1])
    tracked = set(git("ls-files").split("\n"))
    return {"ok": True, "files": files, "untracked": [f for f in files if f not in tracked],
            "ns1e": [f for f in files if "ns1e" in f]}


def source(a) -> int:
    L = Ledger()
    for tag, sha in TAG_SHA.items():
        got = git("rev-parse", f"{tag}^{{commit}}").strip()
        L.check(f"tag {tag} -> {sha[:12]}", got == sha, got)
    for name, tag in SOURCES.items():
        rel = f"tools/greedy_foveal/{name}"
        frozen = git("show", f"{TAG_SHA[tag]}:{rel}")
        current = (REPO / rel).read_text(encoding="utf-8")
        same_exec = executable_dump(current) == executable_dump(frozen)
        kind = "byte-identical" if current == frozen else "docstrings / comments only" if same_exec else "EXECUTABLE"
        L.check(f"{rel} executable-equal to {tag}", same_exec, kind)
    imp = host_import_closure()
    L.check("host import closure loads", imp["ok"], imp.get("error"))
    if imp["ok"]:
        L.check("host import closure: every loaded repository module is tracked", not imp["untracked"],
                imp["untracked"])
        L.check("host import closure: no NS1e-lineage module", not imp["ns1e"], imp["ns1e"])
        L.report("host_import_closure", imp["files"])
    return finish(L, None, "SOURCE")


# ------------------------------------------------------------------ run mode
def compare_run(run: Path, base: Path, prefix: bool, known: bool) -> Ledger:
    L = Ledger()
    tr, tb = read_json(run / "trajectory.json"), read_json(base / "trajectory.json")
    TR, TB = tr["trajectory"], tb["trajectory"]
    n_r, n_b = len(TR), len(TB)
    L.report("fixations", {"run": n_r, "baseline": n_b})

    # ---- run-level records
    if prefix:
        L.check("prefix: the run is not longer than the baseline", n_r <= n_b, f"{n_r} vs {n_b}")
        fields = SUMMARY_PREFIX
    else:
        L.check("fixation count", n_r == n_b, f"{n_r} vs {n_b}")
        fields = SUMMARY_EXACT
    diff = [k for k in fields if tr.get(k, KeyError) != tb.get(k, KeyError)]
    L.check("trajectory summary fields (" + ("prefix set" if prefix else "all control fields") + ")", not diff,
            {k: [tr.get(k), tb.get(k)] for k in diff[:MAX_LISTED]} or None)
    L.report("code", {"run": tr.get("code"), "baseline": tb.get("code")})
    L.report("wall_seconds", {"run": tr.get("wall_seconds"), "baseline": tb.get("wall_seconds")})

    # ---- per fixation, in order
    n = min(n_r, n_b)
    bad_entry, bad_calib, bad_pts, missing = {}, [], {}, []
    rgb_pts: dict = {}
    for i in range(n):
        er, eb = TR[i], TB[i]
        last_of_prefix = prefix and i == n_r - 1 and n_r < n_b
        ignore = ENTRY_METADATA + (("next", "local_candidates") if last_of_prefix else ())
        d = entry_differences(er, eb, ignore)
        if d:
            bad_entry[er.get("n", i + 1)] = d
        k = int(eb["n"])
        fr, fb = run / f"fixations/fix-{k:04d}", base / f"fixations/fix-{k:04d}"
        if not ((fr / "calibration.json").is_file() and (fr / "points.npz").is_file()):
            missing.append(k)
            continue
        if (fr / "calibration.json").read_bytes() != (fb / "calibration.json").read_bytes():
            bad_calib.append(k)
        pr, pb = npz_payload(fr / "points.npz", POINTS_BITWISE), npz_payload(fb / "points.npz", POINTS_BITWISE)
        bad = [key for key in POINTS_BITWISE if key not in pr or key not in pb or not bitwise_equal(pr[key], pb[key])]
        if pr["_keys"] != pb["_keys"]:
            bad.append("archive keys")
        if bad:
            bad_pts[k] = bad
        merge_rgb(rgb_pts, rgb_difference(pr.get("rgb"), pb.get("rgb")))
    L.check(f"per-fixation records 1..{n} (gaze, kind, decision, candidates, correspondence, fusion, coverage, "
            "SEEN / DEPTH, diagnostic error)", not bad_entry, dict(list(bad_entry.items())[:MAX_LISTED]) or None)
    seq_r = [e["kind"] for e in TR[:n]]
    seq_b = [e["kind"] for e in TB[:n]]
    L.check(f"LOCAL / GLOBAL sequence 1..{n}", seq_r == seq_b)
    gz_r = [(e["yaw_deg"], e["pitch_deg"]) for e in TR[:n]]
    gz_b = [(e["yaw_deg"], e["pitch_deg"]) for e in TB[:n]]
    L.check(f"fixation directions in order 1..{n}", gz_r == gz_b)
    L.check(f"per-fixation files present 1..{n}", not missing, missing[:MAX_LISTED] or None)
    L.check(f"calibration.json byte-identical 1..{n}", not bad_calib, bad_calib[:MAX_LISTED] or None)
    L.check(f"points.npz {'/'.join(POINTS_BITWISE)} bitwise 1..{n}", not bad_pts,
            dict(list(bad_pts.items())[:MAX_LISTED]) or None)
    L.report("points_rgb_difference (presentation only, not compared)", rgb_pts)

    # ---- the saved decision states (one per decision)
    n_dec = n_r - 1 if prefix else n
    bad_pol, missing_pol = [], []
    for k in range(1, n_dec + 1):
        p_r, p_b = run / f"policy/state-{k:04d}.npz", base / f"policy/state-{k:04d}.npz"
        if p_r.is_file() != p_b.is_file():
            missing_pol.append(k)
            continue
        if not p_r.is_file():
            continue
        sr, sb = npz_payload(p_r, POLICY_BITWISE), npz_payload(p_b, POLICY_BITWISE)
        if sr["_keys"] != sb["_keys"] or not all(bitwise_equal(sr[key], sb[key]) for key in POLICY_BITWISE):
            bad_pol.append(k)
    if not prefix:
        extra = {p.name for p in (run / "policy").glob("state-*.npz")} ^ {p.name for p in
                                                                          (base / "policy").glob("state-*.npz")}
        missing_pol += sorted(extra)
    L.check(f"policy decision states present in both 1..{n_dec}", not missing_pol, missing_pol[:MAX_LISTED] or None)
    L.check(f"policy decision states bitwise 1..{n_dec}", not bad_pol, bad_pol[:MAX_LISTED] or None)

    # ---- coverage
    cr = npz_payload(run / "coverage.npz", COVERAGE_BITWISE)
    cb = npz_payload(base / "coverage.npz", COVERAGE_BITWISE)
    if prefix:
        L.check("coverage.npz row weights bitwise", bitwise_equal(cr["row_weights"], cb["row_weights"]))
        L.check(f"SEEN history 1..{n_r} bitwise", bitwise_equal(cr["seen_history"], cb["seen_history"][:n_r]))
        L.check(f"DEPTH history 1..{n_r} bitwise", bitwise_equal(cr["depth_history"], cb["depth_history"][:n_r]))
        ref_state = (npz_payload(base / f"policy/state-{n_r:04d}.npz", ("state",))["state"] if n_r < n_b
                     else cb["state"])
        L.check(f"coverage state after fixation {n_r} bitwise", bitwise_equal(cr["state"], ref_state))
    else:
        bad = [k for k in COVERAGE_BITWISE if not bitwise_equal(cr[k], cb[k])]
        L.check("coverage.npz state / SEEN history / DEPTH history / row weights bitwise",
                not bad and cr["_keys"] == cb["_keys"], bad or None)

    # ---- freeze integrity of the run under test, and the Breadth-1 firewall
    fz = read_json(run / "freeze.json")
    stale = [f for f, h in fz["files"].items() if sha256(run / f) != h]
    L.check("run products unchanged since its freeze", not stale, stale or None)
    L.check("control process opened no Breadth-1 path (run)", fz["host_open_audit"]["breadth1_opens"] == [])
    fzb = read_json(base / "freeze.json")
    L.report("freeze_hashes_equal_to_baseline (informative; RGB and run metadata change some file bytes)",
             {f: fz["files"].get(f) == h for f, h in fzb["files"].items()})
    L.report("host_open_audit", {"run": fz["host_open_audit"]["opens_recorded"],
                                 "baseline": fzb["host_open_audit"]["opens_recorded"]})

    # ---- run checks
    if (run / "checks.json").is_file():
        ck = read_json(run / "checks.json")
        L.check("run.py checks: all pass (run)", ck.get("all_pass") is True)
        if not prefix and (base / "checks.json").is_file():
            L.check("run.py checks: equal check values", ck["checks"] == read_json(base / "checks.json")["checks"])
    else:
        L.check("run.py checks recorded (checks.json)", False, "missing")

    if prefix:
        return L

    # ---- final map
    mr, mb = npz_payload(run / "final-map.npz", MAP_BITWISE), npz_payload(base / "final-map.npz", MAP_BITWISE)
    bad = [k for k in MAP_BITWISE if not bitwise_equal(mr[k], mb[k])]
    L.check("final-map.npz keys", mr["_keys"] == mb["_keys"], [mr["_keys"], mb["_keys"]])
    L.check(f"final-map.npz {' / '.join(MAP_BITWISE)} bitwise", not bad, bad or None)
    L.report("final_map_surfels", {"run": int(len(mr["xyz_h"])), "baseline": int(len(mb["xyz_h"]))})
    L.report("final_map_rgb_difference (presentation only, not compared)", rgb_difference(mr["rgb"], mb["rgb"]))
    del mr, mb
    L.check("final-map-oracle-segmentation.ply byte-identical",
            sha256(run / "final-map-oracle-segmentation.ply") == sha256(base / "final-map-oracle-segmentation.ply"))
    hr, pr = ply_split(run / "final-map.ply")
    hb, pb = ply_split(base / "final-map.ply")
    xyz_same = hr == hb and all(bitwise_equal(pr[c], pb[c]) for c in "xyz")
    L.check("final-map.ply header and XYZ bitwise", xyz_same)
    L.report("final_map_ply_colour_difference (presentation only, not compared)",
             rgb_difference(np.stack([pr[c] for c in "rgb"], 1), np.stack([pb[c] for c in "rgb"], 1)))
    del pr, pb

    # ---- post-hoc evaluation
    if (run / "evaluation.json").is_file() and (base / "evaluation.json").is_file():
        er, eb = read_json(run / "evaluation.json"), read_json(base / "evaluation.json")
        bad = [k for k in EVAL_EXACT if er.get(k, KeyError) != eb.get(k, KeyError)]
        xr = {k: v for k, v in er["explorer"].items() if k not in EVAL_EXPLORER_METADATA}
        xb = {k: v for k, v in eb["explorer"].items() if k not in EVAL_EXPLORER_METADATA}
        if xr != xb:
            bad.append("explorer")
        L.check("evaluation.json coverage blocks, NN distances, reference and cross-check", not bad, bad or None)
        L.check("evaluation freeze link: evaluation names the run's own freeze",
                er["freeze_sha256"] == sha256(run / "freeze.json"))
        vr = npz_payload(run / "evaluation.npz", EVAL_NPZ_BITWISE)
        vb = npz_payload(base / "evaluation.npz", EVAL_NPZ_BITWISE)
        bad = [k for k in EVAL_NPZ_BITWISE if not bitwise_equal(vr[k], vb[k])]
        L.check("evaluation.npz cells / covered / instance bitwise", not bad, bad or None)
        p = er["primary_all_geometry"]
        L.report("evaluation_all_geometry", p)
    else:
        L.check("post-hoc evaluation present in both runs", False)

    # ---- the literal frozen known answer (independent of the baseline files)
    if known:
        ev = read_json(run / "evaluation.json") if (run / "evaluation.json").is_file() else None
        got = {"fixations": tr["fixations"], "stop_reason": tr["stop_reason"], "local_saccades": tr["local_saccades"],
               "global_saccades": tr["global_saccades"], "seen_pct": f"{100 * tr['final_seen_fraction']:.2f}",
               "depth_pct": f"{100 * tr['final_depth_fraction']:.2f}"}
        if ev:
            p = ev["primary_all_geometry"]
            got |= {"covered_cells": p["covered_cells"], "reference_cells": p["reference_cells"],
                    "cell_pct": f"{100 * p['cell_coverage']:.2f}", "solid_angle_pct": f"{100 * p['solid_angle_coverage']:.2f}"}
        wrong = {k: [got.get(k), v] for k, v in KNOWN_ANSWER.items() if got.get(k) != v}
        L.check("known answer: 542 / SEEN >= 99 % / 99.00 % / 98.28 % / 322 local / 219 global / 98.52 % cells "
                "(251,966 / 255,758) / 98.32 % sr", not wrong, wrong or None)
        L.report("known_answer_observed", got)
    return L


def run_mode(a) -> int:
    run, base = Path(a.run).resolve(), Path(a.baseline).resolve()
    L = compare_run(run, base, a.prefix, a.known_answer)
    out = Path(a.out) if a.out else run / ("equivalence-prefix.json" if a.prefix else "equivalence.json")
    return finish(L, {"schema": "GFE-equivalence", "run": str(run), "baseline": str(base), "prefix": a.prefix,
                      "known_answer": a.known_answer, "code": git("rev-parse", "HEAD").strip()}, "RUN", out)


# ------------------------------------------------------------------ selftest
def selftest(a) -> int:
    """Each comparator must accept an identical input and reject a minimally perturbed one."""
    L = Ledger()
    src = git("show", f"{IMPL_SHA}:tools/greedy_foveal/explorer.py")
    base = executable_dump(src)
    L.check("source: identical text accepted", executable_dump(src) == base)
    doc = src.replace("the host-side pieces of FIXATE", "the host-side parts of FIXATE", 1)
    L.check("source: docstring-only change accepted", doc != src and executable_dump(doc) == base)
    com = src.replace("# 7.2 deg: neighbour centre offset", "# neighbour offset", 1)
    L.check("source: comment-only change accepted", com != src and executable_dump(com) == base)
    const = src.replace("EDGE_MIN = 0.25", "EDGE_MIN = 0.26", 1)
    L.check("source: changed executable constant rejected", const != src and executable_dump(const) != base)
    op = src.replace("if radius > cell:", "if radius >= cell:", 1)
    L.check("source: changed comparison operator rejected", op != src and executable_dump(op) != base)

    rng = np.random.default_rng(0)
    xyz = rng.normal(size=(1000, 3))
    ulp = xyz.copy()
    ulp[517, 1] = np.nextafter(ulp[517, 1], np.inf)
    L.check("bitwise: identical array accepted", bitwise_equal(xyz, xyz.copy()))
    L.check("bitwise: one-ULP change rejected", not bitwise_equal(xyz, ulp))
    L.check("bitwise: dtype change rejected", not bitwise_equal(xyz, xyz.astype(np.float32)))
    L.check("bitwise: -0.0 vs +0.0 rejected", not bitwise_equal(np.array([0.0]), np.array([-0.0])))
    seen = np.cumsum(rng.random(50)) / 100
    seen2 = seen.copy()
    seen2[31] = np.nextafter(seen2[31], 0)
    L.check("SEEN history: one-ULP change rejected", not bitwise_equal(seen, seen2))

    e = {"n": 7, "kind": "local", "yaw_deg": 7.2, "pitch_deg": -1.5, "next": {"kind": "local", "dir": "NE"},
         "fusion": {"matched": 10, "new": 5}, "seconds": {"total": 1.0}, "render_seconds_lr": {"L": 0.3}}
    e_time = json.loads(json.dumps(e)) | {"seconds": {"total": 9.0}, "render_seconds_lr": {"L": 0.9}}
    L.check("entry: timing-only difference accepted", not entry_differences(e, e_time, ENTRY_METADATA))
    e_kind = json.loads(json.dumps(e)) | {"next": {"kind": "global", "dir": "NE"}}
    L.check("entry: flipped decision kind rejected", entry_differences(e, e_kind, ENTRY_METADATA) == ["next"])
    e_fus = json.loads(json.dumps(e))
    e_fus["fusion"]["new"] = 6
    L.check("entry: changed fusion count rejected", entry_differences(e, e_fus, ENTRY_METADATA) == ["fusion"])
    e_gaze = json.loads(json.dumps(e)) | {"yaw_deg": float(np.nextafter(7.2, 8.0))}
    L.check("entry: one-ULP gaze change rejected", entry_differences(e, e_gaze, ENTRY_METADATA) == ["yaw_deg"])
    e_key = {k: v for k, v in e.items() if k != "fusion"}
    L.check("entry: missing key rejected", entry_differences(e, e_key, ENTRY_METADATA) == ["fusion"])
    return finish(L, None, "SELFTEST")


# ------------------------------------------------------------------ output
def finish(L: Ledger, meta: dict | None, label: str, out: Path | None = None) -> int:
    for name, r in L.results.items():
        tail = f"  {r['detail']}" if "detail" in r and r["detail"] not in (None, [], {}) else ""
        print(f"{PREFIX} {'PASS' if r['pass'] else 'FAIL'} {name}{tail if (not r['pass'] or len(str(tail)) < 120) else ''}",
              flush=True)
    for name, v in L.reported.items():
        if name != "host_import_closure":
            print(f"{PREFIX} REPORT {name}: {json.dumps(v)}", flush=True)
    if out is not None:
        Path(out).write_text(json.dumps({**(meta or {}), "all_pass": L.all_pass, "checks": L.results,
                                         "reported": L.reported}, indent=1, sort_keys=True) + "\n")
        print(f"{PREFIX} wrote {out}", flush=True)
    passed = sum(r["pass"] for r in L.results.values())
    print(f"{PREFIX} {label} {'PASS' if L.all_pass else 'FAIL'} ({passed}/{len(L.results)} checks passed)"
          + ("" if L.all_pass else f"; {len(L.failures())} failed: {L.failures()}"), flush=True)
    return 0 if L.all_pass else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("source")
    sub.add_parser("selftest")
    r = sub.add_parser("run")
    r.add_argument("--run", required=True)
    r.add_argument("--baseline", required=True)
    r.add_argument("--prefix", action="store_true", help="compare a shorter run with the first N baseline fixations")
    r.add_argument("--known-answer", action="store_true", help="also assert the literal frozen grow600 numbers")
    r.add_argument("--out", default=None, help="record path (default: RUN/equivalence[-prefix].json)")
    a = ap.parse_args()
    return {"source": source, "selftest": selftest, "run": run_mode}[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())
