"""Natural Bootstrap-1b: fail-capable checks of foveal serviceability.

    .venv/bin/python tools/natural_bootstrap/check_nb1b.py --run RUN --visuals VIS [--corruptions] [--write-summary]

Contract: docs/natural-bootstrap/nb1b-foveal-serviceability-contract.md, section 14 (checks 1-33).  The
checker keeps its own literal constants and recomputes independently:
- its own grid directions (yaw / pitch formulas);
- angular distance via the chord formula 2 asin(||d_s - d_i|| / 2);
- footprints, containment, the environment role and the classes, from the frozen NB1a labels, seeds,
  clearances and supports, with the classes found as "exactly one rule holds";
- R_FULL from atan(sqrt(2) tan 6 deg) and from the corner direction of the square core;
- the queue order, and the reference composition from the NB1a overlap matrix.

``--corruptions`` plants defects in throwaway mirrors (JSON copied, other files linked) or as in-process
mutants.  They count only when the uncorrupted baseline passes.  ``--write-summary`` writes only
``check-summary.json``.
"""
from __future__ import annotations

import argparse
import ast
import contextlib
import hashlib
import io
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PREFIX = "[nb1b-check]"

# ---- literal copies (contract sections 2-9); deliberately not imported from nb1b_spec
W, H = 720, 360
N = W * H
CORE_FOV = 12.0
R_CENTER = math.radians(6.0)
R_FULL = math.atan(math.sqrt(2.0) * math.tan(math.radians(6.0)))
EPS = 1e-12
TWO_PI = 2.0 * math.pi
NB1A_COUNT = 453
ENV, PRI, SEC, MAR, EDG = "ENVIRONMENT_CANDIDATE", "PRIMARY_LOOK", "SECONDARY_LOOK", "MARGINAL", "EDGE_ONLY"
CLASSES = [ENV, PRI, SEC, MAR, EDG]
BASE = "9c01b8a62813d097940ad5e6e3e95c5d3e3ead83"
NB1A_ACCEPTED = "dcd294fc7dead16e9d492e8c0fd03a3e3df11e02"
SHARED = Path("/home/lvelho/rd/f3d-vision")
NB1A_RUN = SHARED / "previews/natural-bootstrap-1a-range-connectivity"
NB1A_VIS = SHARED / "visuals/natural-bootstrap-1a-range-connectivity"
NB1A_FREEZE_SHA = "c0236d0424a7724bfe57bf0a19bdf56899b7eadf5e059c9537e785f3a08b826a"
SELECTION_INPUTS = {
    "bootstrap-freeze.json": "c0236d0424a7724bfe57bf0a19bdf56899b7eadf5e059c9537e785f3a08b826a",
    "hypothesis-raster.npz": "513a15e0077fc1f5d84847ff020386687ce7ec28477b71ddc349378fb00bae88",
    "hypotheses.json": "eecf180faecd7765e15c162b76ae1427dc12212026f439d608f21b9c4357009b",
    "seeds.json": "c0362d9c898303869117bdd3bb303dadaf15c2d19b94733467fe2ade7c1fb556",
    "discovery-summary.json": "fac0adb39331d9ff2a3305791b2aff3f0edbd2a43503d3d3572437a74cf2e4ec",
}
EVAL_INPUTS = {
    "input/rgb-sensory.npz": "cd2600e678fe7f33471e50bee5443128dd5470cc2b380eb7b34a22d3e4ad2c3e",
    "evaluation/overlap-summary.json": "1ad980a4a84af7e0e63b6f81360c85c77e3863d7baa324bf45bcdedfe65691cb",
    "evaluation/overlap-matrix.npz": "e4f4bde03d2bfb82cc8a44ab6cbc3b74afec624677051da6fc882c96e502462d",
    "evaluation/reference-cells.npz": "54a58d28eab4ade81c7e945fefb379ce6d13f5a149797324bdbb23f1f84f9f76",
}
NB1A_RUN_FILES = {   # the whole accepted NB1a run tree (unchanged by NB1b)
    "check-summary.json": "7eee407a66a75c928537c4ea7e06c74014732a06b70dfa60621aaf880018f74b",
    "discovery/bootstrap-freeze.json": "c0236d0424a7724bfe57bf0a19bdf56899b7eadf5e059c9537e785f3a08b826a",
    "discovery/continuity-edges.npz": "149ce63dbae20789c502f1116f032221ea19e2d4151bdef3f03fe6dda8389511",
    "discovery/discovery-opened-files.json": "9de6577423da18c819d563bf1296b0775113b4dd71b0117964a2ec37a8ddb669",
    "discovery/discovery-summary.json": "fac0adb39331d9ff2a3305791b2aff3f0edbd2a43503d3d3572437a74cf2e4ec",
    "discovery/hypotheses.csv": "ca45849740863fbf1b4d80bf34e432da26e4501dbf2fbfeb7922a16ddf0fa9e9",
    "discovery/hypotheses.json": "eecf180faecd7765e15c162b76ae1427dc12212026f439d608f21b9c4357009b",
    "discovery/hypothesis-raster.npz": "513a15e0077fc1f5d84847ff020386687ce7ec28477b71ddc349378fb00bae88",
    "discovery/seeds.json": "c0362d9c898303869117bdd3bb303dadaf15c2d19b94733467fe2ade7c1fb556",
    "evaluation/evaluation-opened-files.json": "92ec643716b324d4648b30f7e1b5a0e8b8e32ff7fcd163ca2bd77eb90c502d08",
    "evaluation/overlap-matrix.npz": "e4f4bde03d2bfb82cc8a44ab6cbc3b74afec624677051da6fc882c96e502462d",
    "evaluation/overlap-summary.json": "1ad980a4a84af7e0e63b6f81360c85c77e3863d7baa324bf45bcdedfe65691cb",
    "evaluation/reference-cells.npz": "54a58d28eab4ade81c7e945fefb379ce6d13f5a149797324bdbb23f1f84f9f76",
    "evaluation/rgb-edge-contrast.npz": "a065901f7ff1d069bfa660614d2761e71c3dcde272f17e93c78d0c54ca81829d",
    "evaluation/rgb-edge-diagnostics.json": "7ea56745ff2894526406b57e0786c74ff67920b162fb0031a02c93259e276d25",
    "input/input-manifest.json": "6d2547021a2abf71916118b3780a5e97b78e5687539cfd96f4d32de3b345dfaa",
    "input/input-opened-files.json": "a2138087173781c8a74c18de5dfc662a55eec34fff59a85ff1789c2a3416f4b7",
    "input/range-sensory.npz": "02bdf22472ab542545102ec5c3c7f092953a1f89ee2f61ebe62225545ed0883b",
    "input/rgb-sensory.npz": "cd2600e678fe7f33471e50bee5443128dd5470cc2b380eb7b34a22d3e4ad2c3e",
    "manifest.json": "69021c636ef735edf425dab82504473d973735ddeb8109d06ca1e6ebb12fe12e",
    "process-log.jsonl": "fcd7288cdec4f17fd1578c4aa0bb4c2b2fd509c957c745fb7475d81ef4f7a3cf",
    "synthetic/synthetic-report.json": "df3036492e29536a2d5f9183535de61bcead971605e02bacb06038aa2f4616fc",
}
NB1A_VIS_FILES = {
    "overview.png": "eb3348767ce0bbb80c6edd623f051bd1e98aac4172eb4d687318a66dc2e19140",
    "range-input.png": "8c066be058a181609746dcce5539dc86159385324c792dd7b04b983507b3e8e9",
    "continuity-boundaries.png": "41cd53bf17bfd0dfb1ef3905d4fb32530cb65254cc8b6fe4b0a6b9572056632a",
    "hypothesis-support-histogram.png": "d295006ad83e204cf27f369582c236466faa2b447187078c437bf7cfadc7d0ad",
    "interior-clearance-histogram.png": "4e4550441326ec9b22815f19aeca3039be8a4786ad9a7a517c72c16884d37fef",
    "overlap-matrix.png": "032ca85e3399d44d4c6919c480e3d375cc2317353113a2d09e907c814f6efd93",
    "hypothesis-panorama.png": "c0471cf98e02dd3f97c9486a32073c0c3722faaf80f25324456ded1e887f7b28",
    "seed-panorama.png": "f4b853a900f0be0f0eefe78d55b71634bdc03c30370886cc10e505cb35492fd7",
    "rgb-edge-contrast.png": "2ed52df43cdf16a14639534b1842e80d657fe22fd8c77e9f70529d8f276c4ecc",
    "visuals-manifest.json": "78d9d96c6002f571a85f5adac20cf3ed3aabe9270ab068e4541c1ffec78ceecc",
}
SENSOR_SHA = "ae3779bc5cbe8f9702227ae9f123c6be1abe394a0a3c617627f38f171c556c54"
RENDER_PATH = SHARED / "previews/breadth-1-classroom-234-spherical-glance/render"
RENDER_DIR = {"canonical.exr": "4ea036fc74eab3b3ab06a0c4470c2b01740c9322de0eea522f957ddfffa172f8",
              "render-metadata.json": "7c05b80d2d0291f8e12c0886008957b2579e27561b78a766e156b29ec2282157"}
FROZEN = ["../source/nb1a-source-manifest.json", "serviceability.json", "serviceability.csv", "primary-look-queue.json",
          "secondary-look-queue.json", "environment-candidate.json", "footprint-stats.json", "footprints.npz",
          "selection-summary.json", "selection-opened-files.json"]
SELECTION_CODE = ["nb1b_spec.py", "nb1b_serviceability.py", "nb1a_spec.py", "nb1a_discovery.py", "nb1a_guard.py",
                  "fsg_geometry.py"]
NB1B_FILES = {"docs/natural-bootstrap/nb1b-foveal-serviceability-contract.md",
              "docs/natural-bootstrap/nb1b-foveal-serviceability-report.md",
              "tools/repository/check_repository_layout.py"} | {
    f"tools/natural_bootstrap/{n}" for n in ("nb1b_spec.py", "nb1b_serviceability.py", "nb1b_run.py", "nb1b_visuals.py",
                                             "check_nb1b.py")}
COMMANDS = {"synthetic", "select", "freeze", "evaluate", "visualize"}
FORBIDDEN_IMPORTS = re.compile(r"^(fov3d\.control|fov3d\.experiments\.classroom_oracle\.controller|classroom_oracle1_run|"
                               r"classroom_oracle1_matcher|classroom_oracle1_epistemic|classroom_oracle1_eval|"
                               r"multiobject2c_policy|fsg6f|fsg3_surface_map|fsg_stereo|controller0|bpy|exr_lite|OpenEXR)")
SELECTION_IMPORTS = {"__future__", "json", "math", "numpy", "pathlib", "sys", "nb1a_discovery", "nb1a_spec", "nb1b_spec",
                     "fsg_geometry"}
EVAL_KEYS = re.compile(r"o0|catalog|authored|rgb|object.?index|composition|dominant|reference", re.IGNORECASE)
FIGURES = ["overview.png", "serviceability-panorama.png", "primary-look-panorama.png", "secondary-look-panorama.png",
           "environment-candidate.png", "footprint-examples.png", "class-counts.png"]
STAT_KEYS = ("total_cells", "own_cells", "other_cells", "other_hypotheses", "invalid_cells", "containment_fraction",
             "boundary_tie_cells", "safe")
_CACHE: dict = {}


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git(*args) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout


# ------------------------------------------------------------------ independent geometry and classification
def directions() -> np.ndarray:
    if "dirs" not in _CACHE:
        lon = np.radians(-180.0 + 0.5 * (np.arange(W) + 0.5))
        lat = np.radians(90.0 - 0.5 * (np.arange(H) + 0.5))
        x = np.outer(np.cos(lat), np.sin(lon)); y = np.repeat(np.sin(lat)[:, None], W, 1)
        z = -np.outer(np.cos(lat), np.cos(lon))
        _CACHE["dirs"] = np.stack([x, y, z], -1).reshape(-1, 3)
    return _CACHE["dirs"]


def chord_alpha(d_s: np.ndarray, dirs: np.ndarray) -> np.ndarray:
    return 2.0 * np.arcsin(np.minimum(np.linalg.norm(dirs - d_s, axis=1) / 2.0, 1.0))


def fold_support(rows: np.ndarray) -> float:
    n = np.bincount(rows, minlength=H)
    m = n[:H // 2] + n[::-1][:H // 2]
    ds = [math.sin(math.pi / 2 - k * math.pi / H) - math.sin(math.pi / 2 - (k + 1) * math.pi / H) for k in range(H // 2)]
    return (2 * math.pi / W) * math.fsum(int(a) * b for a, b in zip(m.tolist(), ds) if a)


def stats(cells: np.ndarray, alpha: np.ndarray, lab: np.ndarray, label: int, radius: float) -> dict:
    v = lab[cells]
    own, inv = int(np.count_nonzero(v == label)), int(np.count_nonzero(v == 0))
    oth = int(len(v)) - own - inv
    return {"total_cells": int(len(v)), "own_cells": own, "other_cells": oth,
            "other_hypotheses": int(len(np.unique(v[(v != label) & (v != 0)]))), "invalid_cells": inv,
            "containment_fraction": own / len(v), "boundary_tie_cells": int(np.count_nonzero(np.abs(alpha[cells] - radius) <= EPS)),
            "safe": inv == 0 and oth == 0}


def rules(env: bool, full_safe: bool, center_safe: bool, clearance) -> list[str]:
    """Every class whose rule holds (contract sections 6-7); a partition yields exactly one."""
    c = clearance
    return [k for k, ok in ((ENV, env), (PRI, not env and full_safe), (SEC, not env and not full_safe and center_safe),
                            (MAR, not env and not center_safe and c is not None and c > 0),
                            (EDG, not env and c is not None and c == 0)) if ok]


def solve(labels_flat: np.ndarray, hyps: list[dict]) -> dict:
    """Independent footprints, statistics and classes at the given (frozen) seeds."""
    key = ("solve", hashlib.sha256(labels_flat.tobytes()).hexdigest(),
           json.dumps([(h["label"], h["seed"]["row"], h["seed"]["col"], h["seed"]["clearance_rad"], h["support_sr"])
                       for h in hyps]))
    if key in _CACHE:
        return _CACHE[key]
    dirs = directions()
    out = []
    for h in hyps:
        s = h["seed"]
        d_s = dirs[s["row"] * W + s["col"]]
        a = chord_alpha(d_s, dirs)
        cen, ful = np.flatnonzero(a <= R_CENTER + EPS), np.flatnonzero(a <= R_FULL + EPS)
        cs, fs = stats(cen, a, labels_flat, h["label"], R_CENTER), stats(ful, a, labels_flat, h["label"], R_FULL)
        env = h["support_sr"] > TWO_PI
        out.append({"id": h["id"], "label": h["label"], "center_cells": cen, "full_cells": ful, "full_alpha": a[ful],
                    "center": cs, "full": fs, "env": env, "d_s": d_s,
                    "classes": rules(env, fs["safe"], cs["safe"], s["clearance_rad"])})
    _CACHE[key] = out
    return out


def queue_order(recs: list[dict], cls: str) -> list[str]:
    return [r["id"] for r in sorted((r for r in recs if r["class"] == cls),
                                    key=lambda r: (-r["clearance_rad"], -r["support_sr"], r["id"]))]


# ------------------------------------------------------------------ context
class Ctx:
    def __init__(self, run: Path, vis: Path):
        self.run, self.vis = Path(run), Path(vis)
        j = lambda p: json.loads((self.run / p).read_text())  # noqa: E731
        self.source = j("source/nb1a-source-manifest.json")
        self.serv = j("selection/serviceability.json")
        self.recs = self.serv["hypotheses"]
        self.csv = (self.run / "selection/serviceability.csv").read_text().splitlines()
        self.pq = j("selection/primary-look-queue.json")
        self.sq = j("selection/secondary-look-queue.json")
        self.envc = j("selection/environment-candidate.json")
        self.fps = j("selection/footprint-stats.json")
        self.summ = j("selection/selection-summary.json")
        self.sopen = j("selection/selection-opened-files.json")
        self.freeze = j("selection/serviceability-freeze.json")
        self.ref = j("evaluation/candidate-reference-summary.json")
        self.eopen = j("evaluation/evaluation-opened-files.json")
        self.synthetic = j("synthetic/synthetic-report.json")
        self.manifest = j("manifest.json")
        self.processes = [json.loads(l) for l in (self.run / "process-log.jsonl").read_text().splitlines() if l.strip()]
        self.vman = json.loads((self.vis / "visuals-manifest.json").read_text())
        self.fp = dict(np.load(self.run / "selection/footprints.npz"))
        self.nb1a_run = NB1A_RUN
        self.sensor_path = REPO / "tools/fsg_geometry.py"
        self.changed_files = None
        self.fov3d_changed = None
        self.load_nb1a()

    def load_nb1a(self) -> None:
        d = self.nb1a_run / "discovery"
        self.nb1a_hyps = json.loads((d / "hypotheses.json").read_text())["hypotheses"]
        self.nb1a_seeds = json.loads((d / "seeds.json").read_text())["seeds"]
        self.nb1a_summ = json.loads((d / "discovery-summary.json").read_text())
        self.nb1a_freeze = json.loads((d / "bootstrap-freeze.json").read_text())
        with np.load(d / "hypothesis-raster.npz") as z:
            self.labels = np.asarray(z["labels"], np.int64).reshape(-1)

    def solved(self) -> list[dict]:
        return solve(self.labels, self.nb1a_hyps)

    def fp_cells(self, kind: str, k: int) -> np.ndarray:
        p = self.fp[f"{kind}_ptr"]
        return self.fp[f"{kind}_cells"][p[k]:p[k + 1]].astype(np.int64)


def changed_files(ctx) -> list[str]:
    if ctx.changed_files is not None:
        return ctx.changed_files
    ch = set(git("diff", "--name-only", BASE).split()) | set(git("diff", "--name-only", "--cached", BASE).split())
    ch |= {p for p in git("ls-files", "--others", "--exclude-standard").split() if p.startswith(("tools/", "docs/", "fov3d/"))}
    return sorted(ch)


def fov3d_changed(ctx) -> bool:
    if ctx.fov3d_changed is not None:
        return ctx.fov3d_changed
    return (subprocess.run(["git", "diff", "--quiet", BASE, "--", "fov3d"], cwd=REPO).returncode != 0
            or bool(git("ls-files", "--others", "--exclude-standard", "--", "fov3d").strip()))


def _run_root(rec, leaves) -> Path | None:
    """The run root a guard record declared: its write directories must be exactly <root>/<leaf> for ``leaves``."""
    dirs = [Path(p) for p in rec.get("allow_write_dirs", [])]
    roots = {p.parent for p in dirs}
    return roots.pop() if len(roots) == 1 and sorted(p.name for p in dirs) == sorted(leaves) else None


def _imports(path: Path) -> list[str]:
    mods = []
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            mods += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            mods.append(node.module or "")
    return mods


# ------------------------------------------------------------------ checks
def c01(ctx):
    d = ctx.nb1a_run / "discovery"
    fz_sha = sha256(d / "bootstrap-freeze.json")
    files_ok = all(sha256(d / n) == h for n, h in ctx.nb1a_freeze["files"].items()) and len(ctx.nb1a_freeze["files"]) == 8
    code_ok = all(sha256(HERE / n) == h for n, h in ctx.nb1a_freeze["discovery_code"].items())
    inputs_ok = all(sha256(d / n) == h for n, h in SELECTION_INPUTS.items())
    man_ok = (ctx.source["freeze_identity"]["sha256"] == NB1A_FREEZE_SHA
              and {n: v["sha256"] for n, v in ctx.source["selection_inputs"].items()} == SELECTION_INPUTS
              and ctx.source["nb1a"]["accepted_commit"] == NB1A_ACCEPTED
              and ctx.source["nb1a_frozen_files"] == ctx.nb1a_freeze["files"])
    anc = subprocess.run(["git", "merge-base", "--is-ancestor", NB1A_ACCEPTED, "HEAD"], cwd=REPO).returncode == 0
    ok = fz_sha == NB1A_FREEZE_SHA and files_ok and code_ok and inputs_ok and man_ok and anc
    return ok, (f"NB1a freeze {fz_sha[:12]}; frozen products verify {files_ok}; discovery code {code_ok}; inputs {inputs_ok}; "
                f"source manifest {man_ok}; acceptance commit ancestor {anc}")


def c02(ctx):
    bad = [p["command"] for p in ctx.processes if any("blender" in str(a).lower() for a in p["argv"])]
    files = sorted(p.name for p in RENDER_PATH.iterdir())
    same = files == ["blender.log", "canonical.exr", "render-metadata.json"] and all(
        sha256(RENDER_PATH / n) == h for n, h in RENDER_DIR.items())
    return not bad and same, f"Blender in process log: {bad}; Breadth-1 render directory unchanged: {same}"


def c03(ctx):
    bad = [p for p in ctx.processes if p["command"] not in COMMANDS
           or not any(str(a).endswith("nb1b_run.py") for a in p["argv"][:1])
           or any(re.search(r"controller0|classroom_oracle1_run|blender", str(a)) for a in p["argv"])]
    imp = []
    for f in sorted(n for n in NB1B_FILES if n.endswith(".py") and "natural_bootstrap" in n):
        imp += [f"{f}:{m}" for m in _imports(REPO / f) if FORBIDDEN_IMPORTS.match(m)]
    return not bad and not imp, f"non-NB1b processes {[p['command'] for p in bad][:3]}; forbidden imports {imp}"


def c04(ctx):
    a, b = ctx.recs, ctx.nb1a_hyps
    ok = (len(a) == len(b) == NB1A_COUNT == ctx.nb1a_summ["hypotheses"] == ctx.serv["count"]
          == ctx.summ["total_hypotheses"] and all(
              (x["id"], x["label"], x["cells"], x["support_sr"], x["fraction_of_4pi"], x["range_m"])
              == (y["id"], y["label"], y["cells"], y["support_sr"], y["fraction_of_4pi"], y["range_m"]) for x, y in zip(a, b)))
    return ok, f"{len(a)} records vs {len(b)} accepted NB1a hypotheses (declared {NB1A_COUNT}); fields equal {ok}"


def c05(ctx):
    dirs = directions()
    bad = []
    for r, h, s in zip(ctx.recs, ctx.nb1a_hyps, ctx.nb1a_seeds):
        sd = {k: s[k] for k in r["seed"]}
        if r["seed"] != sd or r["seed"] != {k: h["seed"][k] for k in r["seed"]} or set(r["seed"]) != set(
                ("row", "col", "yaw_deg", "pitch_deg", "range_m", "clearance_rad", "fallback", "tied_candidates")):
            bad.append(r["id"]); continue
        if r["clearance_rad"] != h["max_interior_clearance_rad"] or r["clearance_rad"] != s["clearance_rad"]:
            bad.append(r["id"]); continue
        if float(np.max(np.abs(np.array(r["seed_direction_h"]) - dirs[s["row"] * W + s["col"]]))) > 1e-15:
            bad.append(r["id"])
    qbad = [e["id"] for e in ctx.pq["queue"] + ctx.sq["queue"]
            if {k: ctx.recs[int(e["id"][1:]) - 1]["seed"][k] for k in e["seed"]} != e["seed"]]
    return not bad and not qbad, f"seeds differing from NB1a: {bad[:4]}; queue seeds differing: {qbad[:4]}"


def c06(ctx):
    hit = [e["path"] for e in ctx.sopen["events"] if "rgb" in Path(e.get("path", "")).name.lower()]
    return not hit, f"RGB opens during selection: {hit}"


def c07(ctx):
    rec = ctx.sopen
    root = _run_root(rec, ["source", "selection"])
    if root is None or root.name != ctx.run.name:
        return False, f"selection guard write directories {rec.get('allow_write_dirs')}"
    allowed = {str(ctx.nb1a_run / "discovery" / n) for n in SELECTION_INPUTS}
    dreads = {e["path"] for e in rec["events"] if e.get("kind") == "data-read"}
    writes = {e["path"] for e in rec["events"] if e.get("kind") == "write"}
    forb = [p for p in (e.get("path", "") for e in rec["events"])
            if p.endswith(".exr") or "/evaluation/" in p or "instance_catalog" in p or "breadth-1" in p
            or "controller-0" in p or "Object Index" in p or "reference-cells" in p]
    ok_rec = (dreads == allowed and set(rec.get("allow_read", [])) == allowed and not forb and not rec["violations"]
              and rec.get("truth_firewall_violations") == 0 and all(e.get("allowed", True) for e in rec["events"])
              and all(p.startswith((str(root / "source") + "/", str(root / "selection") + "/")) for p in writes))
    bad_imp = []
    for f in ("nb1b_serviceability.py", "nb1b_spec.py"):
        bad_imp += [f"{f}:{m}" for m in _imports(HERE / f) if m.split(".")[0] not in SELECTION_IMPORTS]
    sys.path.insert(0, str(HERE))
    from nb1a_guard import OpenGuard
    blocked = False
    with tempfile.TemporaryDirectory() as td:
        try:
            with OpenGuard("self-test", sorted(allowed), [td]):
                open(ctx.nb1a_run / "evaluation/reference-cells.npz", "rb").close()
        except PermissionError:
            blocked = True
    return ok_rec and not bad_imp and blocked, (f"data reads {sorted(Path(p).name for p in dreads)}; forbidden {forb[:2]}; "
                                                f"violations {len(rec['violations'])}; undeclared imports {bad_imp}; guard "
                                                f"self-test blocks Object Index {blocked}")


def c08(ctx):
    src = ctx.sensor_path
    val = None
    for node in ast.walk(ast.parse(src.read_text())):
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "CORE_FOV_DEG" for t in node.targets):
            val = ast.literal_eval(node.value)
    s = sha256(src)
    ok = (val == CORE_FOV and s == SENSOR_SHA and ctx.source["sensor"]["sha256"] == SENSOR_SHA
          and ctx.source["sensor"]["CORE_FOV_DEG"] == CORE_FOV and ctx.freeze["sensor_constants"]["CORE_FOV_DEG"] == CORE_FOV
          and ctx.serv["config"]["CORE_FOV_DEG"] == CORE_FOV and ctx.freeze["sensor_source"]["sha256"] == SENSOR_SHA)
    return ok, f"tools/fsg_geometry.py declares CORE_FOV_DEG = {val!r}, sha256 {s[:12]}; run used {ctx.source['sensor']['CORE_FOV_DEG']!r}"


def c09(ctx):
    cfgs = [ctx.serv["config"], ctx.freeze["sensor_constants"], ctx.fps["sensor"], ctx.summ["sensor"]]
    used = [ctx.fps["radii_used"]["r_center"], ctx.summ["radii_used"]["r_center"]]
    ok = all(c["R_CENTER_DEG"] == 6.0 and c["R_CENTER_RAD"] == R_CENTER for c in cfgs) and all(u == R_CENTER for u in used)
    return ok, f"R_CENTER declared {[c['R_CENTER_DEG'] for c in cfgs]} deg; used {used} rad (6 deg = {R_CENTER!r})"


def c10(ctx):
    a = math.tan(math.radians(6.0))
    v = np.array([a, a, 1.0])
    corner = math.atan2(float(np.linalg.norm(np.cross(v, [0.0, 0.0, 1.0]))), float(v @ [0.0, 0.0, 1.0]))
    cfgs = [ctx.serv["config"], ctx.freeze["sensor_constants"], ctx.fps["sensor"], ctx.summ["sensor"]]
    used = [ctx.fps["radii_used"]["r_full"], ctx.summ["radii_used"]["r_full"]]
    ok = (abs(corner - R_FULL) <= 1e-15 and all(c["R_FULL_RAD"] == R_FULL for c in cfgs) and all(u == R_FULL for u in used)
          and abs(R_FULL - math.radians(math.sqrt(2) * 6.0)) > 1e-4)
    return ok, f"R_FULL {math.degrees(R_FULL):.6f} deg; corner geometry diff {abs(corner - R_FULL):.2g}; used {used}"


def c11(ctx):
    s = ctx.solved()
    worst = 0.0
    for k, x in enumerate(s):
        cells = ctx.fp_cells("full", k)
        p = ctx.fp["full_ptr"]
        stored = ctx.fp["full_alpha"][p[k]:p[k + 1]]
        if len(stored) != len(cells):
            return False, f"{x['id']}: alpha / cell count mismatch"
        mine = chord_alpha(x["d_s"], directions()[cells])
        worst = max(worst, float(np.max(np.abs(stored - mine))) if len(cells) else 0.0)
    return worst <= 1e-14, f"max |stored alpha - chord formula| {worst:.2g} rad over every FULL footprint"


def _fp_check(ctx, kind: str):
    s = ctx.solved()
    if len(ctx.fp[f"{kind}_ptr"]) != len(s) + 1:
        return False, f"{kind} footprint count {len(ctx.fp[f'{kind}_ptr']) - 1} vs {len(s)}"
    bad = []
    fps = {r["id"]: r for r in ctx.fps["hypotheses"]}
    for k, (x, r) in enumerate(zip(s, ctx.recs)):
        cells = ctx.fp_cells(kind, k)
        if not np.array_equal(cells, x[f"{kind}_cells"]) or r[kind] != x[kind] or fps.get(r["id"], {}).get(kind) != x[kind]:
            bad.append(r["id"])
    return not bad, f"{kind.upper()} footprints / statistics differing from the recomputation: {len(bad)} {bad[:4]}"


def c12(ctx):
    return _fp_check(ctx, "center")


def c13(ctx):
    return _fp_check(ctx, "full")


def c14(ctx):
    bad = [r["id"] for r in ctx.recs for k in ("center", "full") if r[k]["invalid_cells"] > 0 and r[k]["safe"]]
    s = ctx.solved()
    inv = sum(1 for x in s for k in ("center", "full") if x[k]["invalid_cells"] > 0)
    rec_ok = all(r[k]["invalid_cells"] == x[k]["invalid_cells"] for r, x in zip(ctx.recs, s) for k in ("center", "full"))
    return not bad and rec_ok, f"footprints with invalid cells marked SAFE: {bad[:4]}; footprints containing invalid " \
                               f"cells {inv}; counts recompute {rec_ok}"


def c15(ctx):
    s = ctx.solved()
    cfg_ok = (ctx.serv["config"]["ENV_SUPPORT_SR"] == TWO_PI and ctx.freeze["selection_config"]["ENV_SUPPORT_SR"] == TWO_PI
              and ctx.fps["radii_used"]["env_support_sr"] == TWO_PI and ctx.envc["threshold_sr"] == TWO_PI)
    bad = [r["id"] for r, x, h in zip(ctx.recs, s, ctx.nb1a_hyps)
           if r["environment_candidate"] != (h["support_sr"] > TWO_PI) or r["environment_candidate"] != x["env"]
           or (r["class"] == ENV) != (h["support_sr"] > TWO_PI)]
    ids = sorted(r["id"] for r in ctx.recs if r["class"] == ENV)
    listed = sorted(c["id"] for c in ctx.envc["candidates"])
    return cfg_ok and not bad and ids == listed, f"threshold 2 pi {cfg_ok}; mismatches {bad[:4]}; environment {ids}"


def c16(ctx):
    n = sum(1 for r in ctx.recs if r["class"] == ENV)
    return n <= 1 and ctx.envc["count"] == n, f"environment candidates {n}"


def c17(ctx):
    s = ctx.solved()
    bad_cls = [r["id"] for r in ctx.recs if r["class"] not in CLASSES]
    ambiguous = [x["id"] for x in s if len(x["classes"]) != 1]
    ids = [r["id"] for r in ctx.recs]
    cnt = {c: sum(1 for r in ctx.recs if r["class"] == c) for c in CLASSES}
    ok = (not bad_cls and not ambiguous and len(set(ids)) == len(ids) == NB1A_COUNT and cnt == ctx.summ["counts"]
          and sum(cnt.values()) == NB1A_COUNT)
    return ok, f"counts {cnt}; non-classes {bad_cls[:3]}; hypotheses not matching exactly one rule {ambiguous[:3]}"


def _iff(ctx, cls):
    s = ctx.solved()
    bad = [r["id"] for r, x in zip(ctx.recs, s) if (r["class"] == cls) != (x["classes"] == [cls])]
    return not bad, f"{cls} mismatches against the independent rule: {bad[:5]}"


def c18(ctx):
    return _iff(ctx, PRI)


def c19(ctx):
    return _iff(ctx, SEC)


def c20(ctx):
    return _iff(ctx, MAR)


def c21(ctx):
    return _iff(ctx, EDG)


def c22(ctx):
    lab = ctx.labels
    ok_r = set(np.unique(lab[lab > 0]).tolist()) == set(range(1, NB1A_COUNT + 1))
    cnt = np.bincount(lab, minlength=NB1A_COUNT + 1)
    bad = [r["id"] for r in ctx.recs if cnt[r["label"]] != r["cells"]
           or abs(fold_support(np.flatnonzero(lab == r["label"]) // W) - r["support_sr"]) != 0.0] if ok_r else ["labels"]
    ids_ok = [r["id"] for r in ctx.recs] == [f"H{k:04d}" for k in range(1, NB1A_COUNT + 1)]
    raster = sha256(ctx.nb1a_run / "discovery/hypothesis-raster.npz") == SELECTION_INPUTS["hypothesis-raster.npz"]
    csv_rows = len(ctx.csv) - 1 == NB1A_COUNT
    return ok_r and not bad and ids_ok and raster and csv_rows, (f"label set 1..{NB1A_COUNT} {ok_r}; cell / support "
                                                                 f"mismatches {bad[:3]}; ids {ids_ok}; raster unchanged "
                                                                 f"{raster}; csv rows {len(ctx.csv) - 1}")


def c23(ctx):
    bad = []
    for name, q, cls in (("primary", ctx.pq, PRI), ("secondary", ctx.sq, SEC)):
        want = queue_order(ctx.recs, cls)
        got = [e["id"] for e in q["queue"]]
        ranks = [e["rank"] for e in q["queue"]] == list(range(1, len(got) + 1))
        rq = all(ctx.recs[int(i[1:]) - 1]["queue"] == {"name": name, "rank": k} for k, i in enumerate(want, start=1))
        sm = [e["id"] for e in ctx.summ["queues"][name]] == want
        if got != want or not ranks or not rq or not sm or q["count"] != len(want):
            bad.append(name)
    return not bad, f"queues not in declared order: {bad}"


def c24(ctx):
    env = {r["id"] for r in ctx.recs if r["class"] == ENV}
    pq, sq = [e["id"] for e in ctx.pq["queue"]], [e["id"] for e in ctx.sq["queue"]]
    ok = (not env & (set(pq) | set(sq)) and set(pq) == {r["id"] for r in ctx.recs if r["class"] == PRI}
          and set(sq) == {r["id"] for r in ctx.recs if r["class"] == SEC} and len(pq) == len(set(pq))
          and len(sq) == len(set(sq))
          and all(r["queue"] is None for r in ctx.recs if r["class"] not in (PRI, SEC)))
    return ok, f"environment in queues {sorted(env & (set(pq) | set(sq)))}; queue membership exact {ok}"


def c25(ctx):
    sel = ctx.run / "selection"
    hashes_ok = set(ctx.freeze["files"]) == set(FROZEN) and all(sha256(sel / n) == h for n, h in ctx.freeze["files"].items())
    code = {n: (HERE / n if n != "fsg_geometry.py" else ctx.sensor_path) for n in SELECTION_CODE}
    code_ok = set(ctx.freeze["selection_code"]) == set(SELECTION_CODE) and all(
        sha256(p) == ctx.freeze["selection_code"][n] for n, p in code.items())
    cfg_ok = ctx.freeze["selection_config_sha256"] == hashlib.sha256(
        json.dumps(ctx.freeze["selection_config"], sort_keys=True).encode()).hexdigest() \
        and ctx.freeze["selection_config"] == ctx.serv["config"]
    order = ctx.eopen.get("ordered_data_events", [])
    try:
        k = order.index("freeze_verified")
        ok_order = order.index("reference_access_begins") > k
    except ValueError:
        ok_order = False
    return hashes_ok and code_ok and cfg_ok and ok_order, (f"freeze hashes {hashes_ok}; selection code {code_ok}; config "
                                                           f"{cfg_ok}; verified before reference access {ok_order}")


def c26(ctx):
    root = _run_root(ctx.eopen, ["evaluation"])
    writes = {e["path"] for e in ctx.eopen["events"] if e.get("kind") == "write"}
    out = str(root / "evaluation") if root else "\0"
    ok = root is not None and root.name == ctx.run.name and bool(writes) and all(p.startswith(out + "/") for p in writes) \
        and not ctx.eopen["violations"]
    still = all(sha256(ctx.run / "selection" / n) == h for n, h in ctx.freeze["files"].items())
    rf = ctx.ref.get("frozen_selection_sha256") == ctx.freeze["files"] and ctx.ref.get("computed_after_freeze") is True
    return ok and still and rf, f"evaluation writes only under evaluation/ {ok}; frozen outputs unchanged {still}; " \
                                f"evaluation recorded the frozen hashes {rf}"


def c27(ctx):
    refs = {str(ctx.nb1a_run / n) for n in EVAL_INPUTS}
    order = ctx.eopen.get("ordered_data_events", [])
    try:
        k = order.index("freeze_verified")
        ok = not any(o in refs for o in order[:k]) and refs <= set(order[k:])
    except ValueError:
        ok = False
    sel = [e["path"] for e in ctx.sopen["events"] if e.get("path") in refs or "rgb" in e.get("path", "").lower()]
    return ok and not sel, f"reference / RGB only after the freeze verification {ok}; opened by selection {sel[:2]}"


def c28(ctx):
    bad_keys = []

    def walk(x, path):
        if isinstance(x, dict):
            for k, v in x.items():
                if EVAL_KEYS.search(str(k)):
                    bad_keys.append(f"{path}.{k}")
                walk(v, f"{path}.{k}")
        elif isinstance(x, list):
            for v in x[:NB1A_COUNT]:
                walk(v, path)
    for name, doc in (("serviceability", ctx.serv), ("primary", ctx.pq), ("secondary", ctx.sq), ("environment", ctx.envc),
                      ("footprints", ctx.fps), ("summary", ctx.summ)):
        walk(doc, name)
    s = ctx.solved()
    pure = all(r["class"] == x["classes"][0] for r, x in zip(ctx.recs, s) if len(x["classes"]) == 1) and \
        all(len(x["classes"]) == 1 for x in s)
    q = [e["id"] for e in ctx.pq["queue"]] == queue_order(ctx.recs, PRI) and \
        [e["id"] for e in ctx.sq["queue"]] == queue_order(ctx.recs, SEC)
    return not bad_keys and pure and q, f"evaluation-derived fields in selection products {bad_keys[:3]}; classes equal " \
                                        f"the pure-geometry rule {pure}; queues recompute {q}"


def c29(ctx):
    sys.path.insert(0, str(HERE))
    import nb1b_visuals as V
    cur = {n: sha256(ctx.run / n) for n in V.Data.SOURCES}
    cur.update({str(NB1A_RUN / n): sha256(NB1A_RUN / n) for n in V.Data.NB1A})
    if cur != ctx.vman.get("sources"):
        return False, "figure sources changed since the figures were drawn"
    key = ("vis", tuple(sorted(cur.items())))
    if key not in _CACHE:
        figs, _d = V.render_all(ctx.run)
        _CACHE[key] = {n: hashlib.sha256(V.png_bytes(figs[n])).hexdigest() for n in FIGURES}
    want = _CACHE[key]
    bad = [n for n in FIGURES if not (ctx.vis / n).is_file() or sha256(ctx.vis / n) != want[n]
           or ctx.vman["products"][n]["sha256"] != want[n]]
    return not bad, f"{len(FIGURES) - len(bad)}/{len(FIGURES)} figures regenerate byte-identically; differ {bad}"


def c30(ctx):
    ch = fov3d_changed(ctx)
    files = changed_files(ctx)
    ctrl = [f for f in files if f.startswith(("tools/controller/", "fov3d/")) or f in (
        "tools/classroom_oracle1_render.py", "tools/classroom_oracle1_run.py", "tools/fsg6f_frontier.py",
        "tools/fsg_geometry.py")]
    nb1a = [f for f in files if Path(f).name.startswith(("nb1a_", "check_nb1a", "nb1a-"))]
    run_ok = all(sha256(ctx.nb1a_run / n) == h for n, h in NB1A_RUN_FILES.items()) and sorted(
        str(p.relative_to(ctx.nb1a_run)) for p in ctx.nb1a_run.rglob("*") if p.is_file()) == sorted(NB1A_RUN_FILES)
    vis_ok = all(sha256(NB1A_VIS / n) == h for n, h in NB1A_VIS_FILES.items())
    return not ch and not ctrl and not nb1a and run_ok and vis_ok, (f"fov3d changed {ch}; controller / sensor files changed "
                                                                    f"{ctrl}; NB1a files changed {nb1a}; NB1a run unchanged "
                                                                    f"{run_ok}; NB1a visuals unchanged {vis_ok}")


def c31(ctx):
    extra = [f for f in changed_files(ctx) if f not in NB1B_FILES]
    return not extra, f"undeclared changes vs {BASE[:7]}: {extra[:6]}"


def synthetic_cases():
    """The checker's own known answers (constructed independently of the generator).  Each is
    (name, labels, seeds {label: (row, col, clearance)}, expected classes or 'ambiguous', extra predicate)."""
    d = directions()

    def z():
        return np.zeros(N, np.int64)

    def disk(lab, row, col, deg, value):
        lab[chord_alpha(d[row * W + col], d) <= math.radians(deg) + EPS] = value
        return lab

    def box(lab, r0, r1, cols, value):
        for r in range(r0, r1):
            lab[r * W + np.asarray(cols) % W] = value
        return lab

    def between(lo, hi):
        a = chord_alpha(d[180 * W + 360], d)
        return int(np.count_nonzero((a > math.radians(lo) + EPS) & (a <= math.radians(hi))))
    sq = box(z(), 160, 201, range(340, 381), 1)
    cases = [("FULL-safe square", sq, {1: (180, 360, 0.17)}, {"H0001": PRI}, None),
             ("7 deg disk", disk(z(), 180, 360, 7.0, 1), {1: (180, 360, 0.12)}, {"H0001": SEC}, None),
             ("3 deg disk", disk(z(), 180, 360, 3.0, 1), {1: (180, 360, 0.05)}, {"H0001": MAR}, None),
             ("zero-clearance strip", box(z(), 180, 181, range(300, 421), 1), {1: (180, 360, 0.0)}, {"H0001": EDG}, None)]
    hp = box(box(z(), 0, 181, range(W), 1), 181, H, range(W), 2)
    cases.append(("hemisphere + row", hp, {1: (90, 360, 0.7), 2: (270, 360, 0.7)}, {"H0001": ENV, "H0002": PRI}, None))
    hm = box(box(z(), 0, 179, range(W), 1), 179, H, range(W), 2)
    cases.append(("hemisphere - row", hm, {1: (90, 360, 0.7), 2: (270, 360, 0.7)}, {"H0001": PRI, "H0002": ENV}, None))
    ih = sq.copy(); ih[172 * W + 360] = 0
    cases.append(("invalid hole", ih, {1: (180, 360, 0.06)}, {"H0001": MAR}, lambda x: x[0]["center"]["invalid_cells"] == 1))
    oh = sq.copy(); oh[172 * W + 360] = 2
    cases.append(("other-hypothesis hole", oh, {1: (180, 360, 0.06), 2: (172, 360, 0.0)}, {"H0001": MAR, "H0002": EDG},
                  lambda x: x[0]["center"]["other_cells"] == 1 and x[0]["center"]["invalid_cells"] == 0))
    sm = box(z(), 160, 201, range(-20, 21), 1)

    def shifted(x):
        inner = solve(sq, _hyps(sq, {1: (180, 360, 0.17)}))[0]["full_cells"]
        sh = np.sort((inner // W) * W + (inner % W - 360) % W)
        return np.array_equal(sh, x[0]["full_cells"]) and (x[0]["full_cells"] % W >= 700).any()
    cases.append(("seam square", sm, {1: (180, 0, 0.17)}, {"H0001": PRI}, shifted))
    sh = sm.copy(); sh[180 * W + 714] = 0
    cases.append(("seam hole", sh, {1: (180, 0, 0.05)}, {"H0001": MAR}, None))
    cap = box(z(), 0, 31, range(W), 1)
    cases.append(("pole cap", cap, {1: (3, 100, 0.2)}, {"H0001": PRI}, lambda x: 460 in set(x[0]["full_cells"].tolist())))
    cases.append(("small pole cap", box(z(), 0, 18, range(W), 1), {1: (3, 100, 0.1)}, {"H0001": SEC}, None))
    t6 = disk(z(), 180, 360, 7.0, 1); t6[168 * W + 360] = 0
    cases.append(("6 deg tie", t6, {1: (180, 360, 0.1)}, {"H0001": MAR}, lambda x: x[0]["center"]["boundary_tie_cells"] >= 1))
    t65 = disk(z(), 180, 360, 7.0, 1); t65[167 * W + 360] = 0
    cases.append(("6.5 deg", t65, {1: (180, 360, 0.1)}, {"H0001": SEC}, None))
    cases.append(("tight R_FULL disk", disk(z(), 180, 360, math.degrees(R_FULL), 1), {1: (180, 360, 0.14)}, {"H0001": PRI},
                  lambda x: between(math.degrees(R_FULL), math.sqrt(2) * 6.0) > 0))
    cases.append(("tight R_CENTER disk", disk(z(), 180, 360, 6.0, 1), {1: (180, 360, 0.1)}, {"H0001": SEC},
                  lambda x: between(6.0, 6.5) > 0))
    cases.append(("zero clearance with SAFE CENTER", sq, {1: (180, 360, 0.0)}, "ambiguous", None))
    return cases


def _hyps(lab: np.ndarray, seeds: dict) -> list[dict]:
    return [{"id": f"H{k:04d}", "label": k, "support_sr": fold_support(np.flatnonzero(lab == k) // W),
             "seed": {"row": r, "col": c, "clearance_rad": clr}} for k, (r, c, clr) in sorted(seeds.items())]


def c32(ctx):
    gen = ctx.synthetic
    gen_ok = gen["passed"] and len(gen["cases"]) >= 17 and all(c["ok"] for c in gen["cases"])
    bad = []
    for name, lab, seeds, want, extra in synthetic_cases():
        x = solve(lab, _hyps(lab, seeds))
        if want == "ambiguous":
            if len(x[0]["classes"]) == 1:
                bad.append(name)
            continue
        got = {r["id"]: (r["classes"][0] if len(r["classes"]) == 1 else None) for r in x}
        if got != want or (extra is not None and not extra(x)):
            bad.append(name)
    return gen_ok and not bad, f"generator report {gen_ok} ({len(gen['cases'])} cases); independent known-answer failures {bad}"


def c33(ctx):
    with np.load(ctx.nb1a_run / "evaluation/overlap-matrix.npz") as z:
        h, o, sr = z["h"].astype(np.int64), z["o"].astype(np.int64), z["support_sr"]
    with np.load(ctx.nb1a_run / "evaluation/reference-cells.npz") as z:
        oid = z["object_index"].reshape(-1).astype(np.int64)
    with np.load(ctx.nb1a_run / "input/rgb-sensory.npz") as z:
        rgb = z["srgb8"].reshape(-1, 3).astype(np.float64)
    ovs = json.loads((ctx.nb1a_run / "evaluation/overlap-summary.json").read_text())
    o0_nb1a = {r["id"]: r["O0_fraction"] for r in ovs["per_hypothesis"]}
    pins = all(sha256(ctx.nb1a_run / n) == v for n, v in EVAL_INPUTS.items()) and ctx.ref["reference_inputs_sha256"] == EVAL_INPUTS
    by_id = {r["id"]: (k, r) for k, r in enumerate(ctx.recs)}
    bad = []

    def comp(label, sup):
        m = h == label
        oo, ss = o[m], sr[m]
        o0 = float(ss[oo == 0].sum()) / sup
        cat = float(ss[oo > 0].sum()) / sup
        dom = int(oo[np.lexsort((oo, -ss))[0]]) if len(oo) else None
        return o0, cat, int(np.count_nonzero(oo > 0)), dom
    want_c = sorted([r["id"] for r in ctx.recs if r["class"] in (PRI, SEC)])
    if sorted(c["id"] for c in ctx.ref["candidates"]) != want_c:
        bad.append("candidate set")
    for c in ctx.ref["candidates"] + ctx.ref["environment"]:
        k, r = by_id[c["id"]]
        o0, cat, nauth, dom = comp(r["label"], r["support_sr"])
        if (abs(c["O0_fraction"] - o0) > 1e-12 or abs(c["catalog_fraction"] - cat) > 1e-12 or c["authored_ids_intersected"] != nauth
                or (c["dominant"] or {}).get("o") != dom or abs(o0_nb1a[c["id"]] - o0) > 1e-12):
            bad.append(c["id"]); continue
        full = ctx.fp_cells("full", k)
        fr = c["full_footprint_reference"]
        if fr["cells"] != len(full) or fr["O0_cells"] != int(np.count_nonzero(oid[full] == 0)) or \
                fr["catalog_cells"] != int(np.count_nonzero(oid[full] > 0)):
            bad.append(c["id"] + " footprint"); continue
        if "rgb" in c:
            cen = ctx.fp_cells("center", k)
            if np.max(np.abs(np.array(c["rgb"]["center_footprint_mean_srgb8"]) - rgb[cen].mean(axis=0))) > 1e-9:
                bad.append(c["id"] + " rgb")
    for cls in CLASSES:
        rs = [r for r in ctx.recs if r["class"] == cls]
        sup = math.fsum(r["support_sr"] for r in rs)
        if not rs:
            continue
        o0s = math.fsum(float(sr[(h == r["label"]) & (o == 0)].sum()) for r in rs)
        dom0 = sum(1 for r in rs if comp(r["label"], r["support_sr"])[3] == 0)
        p = ctx.ref["per_class"][cls]
        if p["hypotheses"] != len(rs) or abs(p["O0_fraction"] - o0s / sup) > 1e-9 or p["hypotheses_dominated_by_O0"] != dom0:
            bad.append(f"class {cls}")
    return pins and not bad, f"reference inputs pinned {pins}; recomputation mismatches {bad[:4]}"


CHECKS = [(f"{i:02d}", name, fn) for i, (name, fn) in enumerate([
    ("accepted NB1a source, freeze and products verify", c01), ("no Blender invocation", c02),
    ("no controller invocation", c03), ("all 453 NB1a hypotheses preserved", c04),
    ("NB1a seeds field-identical (no reseeding)", c05), ("selection opened no RGB", c06),
    ("selection opened no Object Index / catalog / evaluation", c07), ("sensor source declares CORE_FOV_DEG = 12.0", c08),
    ("R_CENTER = 6 deg", c09), ("R_FULL = atan(sqrt(2) tan 6 deg), independently", c10),
    ("angular distance recomputes independently", c11), ("CENTER footprints recompute exactly", c12),
    ("FULL footprints recompute exactly", c13), ("invalid cells count as unsafe", c14),
    ("environment criterion is exactly > 2 pi sr", c15), ("at most one environment candidate", c16),
    ("every hypothesis exactly one category", c17), ("PRIMARY iff non-environment and FULL safe", c18),
    ("SECONDARY iff non-environment, FULL unsafe, CENTER safe", c19),
    ("MARGINAL iff non-environment, CENTER unsafe, clearance > 0", c20),
    ("EDGE_ONLY iff non-environment and clearance == 0", c21), ("no hypothesis filtered / deleted / merged / split", c22),
    ("queue ordering recomputes", c23), ("environment excluded from the foreground queues", c24),
    ("freeze hashes matched before evaluation", c25), ("evaluation did not modify frozen outputs", c26),
    ("RGB / reference opened only after the freeze", c27), ("no evaluation datum affects classification or rank", c28),
    ("figures regenerate deterministically", c29), ("fov3d / controllers / sensor / NB1a files unchanged", c30),
    ("changed files are declared NB1b files only", c31), ("synthetic known answers (generator and independent)", c32),
    ("reference evaluation recomputes", c33)], start=1)]


def run_checks(ctx, quiet=False) -> list[dict]:
    res = []
    for num, name, fn in CHECKS:
        try:
            ok, detail = fn(ctx)
        except Exception as exc:
            ok, detail = False, f"{type(exc).__name__}: {exc}"
        res.append({"check": num, "name": name, "ok": bool(ok), "detail": detail})
        if not quiet:
            print(f"{PREFIX} {'PASS' if ok else 'FAIL'} {num} {name}" + ("" if ok else f" -- {detail}"))
    return res


# ------------------------------------------------------------------ corruption suite
def mirror(run: Path, vis: Path, tmp: Path) -> tuple[Path, Path]:
    def copy_tree(src, dst):
        for p in src.rglob("*"):
            q = dst / p.relative_to(src)
            if p.is_dir():
                q.mkdir(parents=True, exist_ok=True)
            elif p.suffix in (".json", ".jsonl", ".csv"):
                q.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(p, q)
            else:
                q.parent.mkdir(parents=True, exist_ok=True); q.symlink_to(p.resolve())
    r, v = tmp / "r" / run.name, tmp / "v" / vis.name   # same directory names as the originals
    copy_tree(run, r); copy_tree(vis, v)
    return r, v


def edit_json(path: Path, fn) -> None:
    d = json.loads(path.read_text()); fn(d); path.write_text(json.dumps(d, indent=1, sort_keys=True) + "\n")


def edit_npz(path: Path, fn) -> None:
    z = dict(np.load(path)); fn(z); path.unlink(); np.savez_compressed(path, **z)   # unlink: never write through a link


def refreeze(m: Path, names=None) -> None:
    """Re-hash the named products into the mirror's freeze, so that only the targeted check can object."""
    def fn(d):
        for n in (names or d["files"]):
            d["files"][n] = sha256(m / "selection" / n)
    edit_json(m / "selection/serviceability-freeze.json", fn)


def regenerate(m: Path, **variant) -> None:
    """Rebuild the mirror's selection products (and synthetic report) with a deliberately wrong variant."""
    sys.path.insert(0, str(HERE))
    import nb1b_run as R
    import nb1b_serviceability as S
    data = S.load_selection_inputs(NB1A_RUN / "discovery")
    note = ""
    try:
        res = S.serviceability(data["labels"], data["hypotheses"], **variant)
    except S.PartitionInvariantError as exc:   # the mutant's selection would STOP; its synthetic report still runs
        res, note = None, f"canonical selection STOPs under this mutant ({exc})"
    if res is not None:
        sel = m / "selection"
        for n in ("serviceability.json", "serviceability.csv", "primary-look-queue.json", "secondary-look-queue.json",
                  "environment-candidate.json", "footprint-stats.json", "footprints.npz", "selection-summary.json"):
            (sel / n).unlink()
        R.write_selection(sel, res)
        R.write_json(sel / "selection-summary.json", S.summary(res, data["summary"]["hypotheses"]))
    results = R.synthetic_results(**variant)
    edit_json(m / "synthetic/synthetic-report.json", lambda d: d.update(cases=results, passed=all(x["ok"] for x in results)))
    refreeze(m)
    return {"note": note} if note else None


def corruptions():
    def edit_recs(m, fn, names=("serviceability.json",)):
        edit_json(m / "selection/serviceability.json", lambda d: fn(d["hypotheses"]))
        refreeze(m, list(names))

    def sensor(m, v, c):
        p = m / "fsg_geometry.py"
        p.write_text(c.sensor_path.read_text().replace("CORE_FOV_DEG = 12.0", "CORE_FOV_DEG = 10.0"))
        return {"sensor_path": p}

    def move_seed(m, v, c):
        tgt = next((r["id"] for r in c.recs if r["class"] in (PRI, SEC)), c.recs[1]["id"])

        def fn(hs):
            for r in hs:
                if r["id"] == tgt:
                    r["seed"]["row"] += 1
        edit_recs(m, fn)
        return {"note": tgt}

    def reclass(m, v, c, frm, to):
        tgt = next((r["id"] for r in c.recs if r["class"] == frm), None)
        if tgt is None:
            return {"not_applicable": f"no {frm} hypothesis"}

        def fn(hs):
            for r in hs:
                if r["id"] == tgt:
                    r["class"] = to
        edit_recs(m, fn)
        return {"note": tgt}

    def env_in_queue(m, v, c):
        env = next((r for r in c.recs if r["class"] == ENV), None)
        if env is None:
            return {"not_applicable": "no environment candidate"}
        edit_json(m / "selection/primary-look-queue.json", lambda d: d["queue"].insert(0, {"rank": 0, "id": env["id"],
                                                                                        "seed": {}}))
        refreeze(m, ["primary-look-queue.json"])

    def delete_edge(m, v, c):
        tgt = next((r["id"] for r in reversed(c.recs) if r["class"] == EDG), None)
        if tgt is None:
            return {"not_applicable": "no EDGE_ONLY hypothesis"}
        edit_json(m / "selection/serviceability.json", lambda d: d.update(
            hypotheses=[r for r in d["hypotheses"] if r["id"] != tgt], count=d["count"] - 1))
        p = m / "selection/serviceability.csv"
        p.write_text("".join(l + "\n" for l in p.read_text().splitlines() if not l.startswith(tgt + ",")))
        refreeze(m, ["serviceability.json", "serviceability.csv"])
        return {"note": tgt}

    def reorder(m, v, c):
        name = "primary" if len(c.pq["queue"]) >= 2 else "secondary"
        q = c.pq if name == "primary" else c.sq
        if len(q["queue"]) < 2:
            return {"not_applicable": "no queue with two entries"}

        def fn(d):
            d["queue"][0], d["queue"][1] = d["queue"][1], d["queue"][0]
        edit_json(m / f"selection/{name}-look-queue.json", fn)
        refreeze(m, [f"{name}-look-queue.json"])

    def rgb_category(m, v, c):
        tgt = next((r["id"] for r in c.recs if r["class"] == MAR), None)
        if tgt is None:
            return {"not_applicable": "no MARGINAL hypothesis"}

        def fn(hs):
            for r in hs:
                if r["id"] == tgt:
                    r["class"] = SEC
                    r["rgb_override"] = {"center_footprint_mean_srgb8": [128.0, 128.0, 128.0]}
        edit_recs(m, fn)
        return {"note": tgt}

    def oid_selection(m, v, c):
        edit_json(m / "selection/selection-opened-files.json", lambda d: d["events"].append(
            {"event": "open", "path": str(NB1A_RUN / "evaluation/reference-cells.npz"), "kind": "data-read", "allowed": True}))
        refreeze(m, ["selection-opened-files.json"])

    def rgb_selection(m, v, c):
        edit_json(m / "selection/selection-opened-files.json", lambda d: d["events"].append(
            {"event": "open", "path": str(NB1A_RUN / "input/rgb-sensory.npz"), "kind": "data-read", "allowed": True}))
        refreeze(m, ["selection-opened-files.json"])

    def ref_before_freeze(m, v, c):
        def fn(d):
            o = [x for x in d["ordered_data_events"] if x != str(NB1A_RUN / "evaluation/reference-cells.npz")]
            o.insert(0, str(NB1A_RUN / "evaluation/reference-cells.npz")); d["ordered_data_events"] = o
        edit_json(m / "evaluation/evaluation-opened-files.json", fn)

    def modify_after_eval(m, v, c):
        p = m / "selection/serviceability.csv"
        p.write_text(p.read_text() + "\n")

    def blender_proc(m, v, c):
        with open(m / "process-log.jsonl", "a") as f:
            f.write(json.dumps({"command": "select", "argv": ["blender", "-b", "x.blend"], "status": "ok"}) + "\n")

    def controller_proc(m, v, c):
        with open(m / "process-log.jsonl", "a") as f:
            f.write(json.dumps({"command": "controller02", "argv": ["fov3d/experiments/classroom_oracle/controller02.py"],
                                "status": "ok"}) + "\n")

    def pixel(m, v, c):
        from PIL import Image
        p = v / "overview.png"
        img = Image.open(p.resolve()).convert("RGB"); img.putpixel((3, 3), (255, 0, 0)); p.unlink(); img.save(p)

    def stat(m, v, c):
        k = next((i for i, r in enumerate(c.recs) if r["class"] in (PRI, SEC)), 1)
        for n in ("serviceability.json", "footprint-stats.json"):
            edit_json(m / "selection" / n, lambda d: d["hypotheses"][k]["center"].update(
                own_cells=d["hypotheses"][k]["center"]["own_cells"] - 1))
        refreeze(m, ["serviceability.json", "footprint-stats.json"])

    def alpha(m, v, c):
        edit_npz(m / "selection/footprints.npz", lambda z: z["full_alpha"].__setitem__(0, z["full_alpha"][0] + 1e-9))
        refreeze(m, ["footprints.npz"])

    def drop_full_cell(m, v, c):
        def fn(z):
            k = 1
            p = z["full_ptr"]
            cut = int(p[k + 1] - 1)
            z["full_cells"] = np.delete(z["full_cells"], cut); z["full_alpha"] = np.delete(z["full_alpha"], cut)
            z["full_ptr"] = np.concatenate([p[:k + 1], p[k + 1:] - 1])
        edit_npz(m / "selection/footprints.npz", fn)
        refreeze(m, ["footprints.npz"])

    def ref_value(m, v, c):
        key = "candidates" if c.ref["candidates"] else "environment"
        if not c.ref[key]:
            return {"not_applicable": "no described candidate"}
        edit_json(m / "evaluation/candidate-reference-summary.json", lambda d: d[key][0].update(
            O0_fraction=d[key][0]["O0_fraction"] + 0.01))

    def synth(m, v, c):
        edit_json(m / "synthetic/synthetic-report.json", lambda d: d["cases"][0].update(ok=False))

    def nb1a_product(m, v, c):
        nb = m / "nb1a" / NB1A_RUN.name
        for p in NB1A_RUN.rglob("*"):
            q = nb / p.relative_to(NB1A_RUN)
            if p.is_dir():
                q.mkdir(parents=True, exist_ok=True)
            else:
                q.parent.mkdir(parents=True, exist_ok=True); q.symlink_to(p.resolve())
        q = nb / "discovery/discovery-summary.json"
        txt = q.read_text(); q.unlink(); q.write_text(txt + "\n")
        return {"nb1a_run": nb}

    return [
        ("CORE_FOV_DEG changed in the sensor source", ("08",), sensor),
        ("R_CENTER of 5.5 deg (regenerated)", ("09", "12"), lambda m, v, c: regenerate(m, r_center=math.radians(5.5))),
        ("R_CENTER of 6.5 deg (regenerated)", ("09", "12"), lambda m, v, c: regenerate(m, r_center=math.radians(6.5))),
        ("R_FULL as sqrt(2) * 6 deg (regenerated)", ("10", "13"),
         lambda m, v, c: regenerate(m, r_full=math.radians(math.sqrt(2) * 6.0))),
        ("invalid cells omitted from footprint failure (regenerated)", ("14", "32"),
         lambda m, v, c: regenerate(m, invalid_unsafe=False)),
        ("seam handling broken (regenerated)", ("12", "13"), lambda m, v, c: regenerate(m, seam_wrap=False)),
        ("> 2 pi rule changed to a fitted 0.3 sr threshold (regenerated)", ("15",),
         lambda m, v, c: regenerate(m, env_support_sr=0.3)),
        ("an NB1a seed moved", ("05",), move_seed),
        ("one PRIMARY reclassified as SECONDARY", ("18",), lambda m, v, c: reclass(m, v, c, PRI, SEC)),
        ("one MARGINAL relabelled EDGE_ONLY", ("20", "21"), lambda m, v, c: reclass(m, v, c, MAR, EDG)),
        ("environment candidate placed in the primary queue", ("24",), env_in_queue),
        ("an EDGE_ONLY hypothesis deleted", ("22",), delete_edge),
        ("a queue reordered", ("23",), reorder),
        ("RGB altered a category", ("28",), rgb_category),
        ("selection read Object Index before the freeze", ("07",), oid_selection),
        ("selection opened RGB", ("06",), rgb_selection),
        ("evaluation read a reference product before the freeze verification", ("27",), ref_before_freeze),
        ("a frozen output modified after evaluation", ("26",), modify_after_eval),
        ("Blender command in the process log", ("02",), blender_proc),
        ("controller command in the process log", ("03",), controller_proc),
        ("a visual pixel altered", ("29",), pixel),
        ("fov3d modified", ("30",), lambda m, v, c: {"fov3d_changed": True}),
        ("controller code modified", ("30",), lambda m, v, c: {"changed_files": changed_files(c) + ["tools/controller/check_controller02.py"]}),
        ("NB1a code modified", ("30",), lambda m, v, c: {"changed_files": changed_files(c) + ["tools/natural_bootstrap/nb1a_discovery.py"]}),
        ("an NB1a frozen product altered", ("01",), nb1a_product),
        ("a footprint statistic altered", ("12",), stat),
        ("a stored angular distance altered", ("11",), alpha),
        ("a FULL footprint cell dropped", ("13",), drop_full_cell),
        ("a reference composition value altered", ("33",), ref_value),
        ("a synthetic known-answer case failed", ("32",), synth),
    ]


def corruption_suite(run: Path, vis: Path) -> tuple[int, int, list]:
    caught = total = 0
    results = []
    for name, targets, fn in corruptions():
        with tempfile.TemporaryDirectory(prefix="nb1b-corrupt-") as td:
            m, v = mirror(run, vis, Path(td))
            with contextlib.redirect_stdout(io.StringIO()):
                overrides = fn(m, v, Ctx(m, v)) or {}
            if "not_applicable" in overrides:
                print(f"{PREFIX} corruption N/A {list(targets)} {name}: {overrides['not_applicable']}")
                results.append({"name": name, "targets": list(targets), "not_applicable": overrides["not_applicable"]})
                continue
            total += 1
            note = overrides.pop("note", "")
            ctx = Ctx(m, v)
            for k, val in overrides.items():
                setattr(ctx, k, val)
            if "nb1a_run" in overrides:
                ctx.load_nb1a()
            with contextlib.redirect_stdout(io.StringIO()):
                res = run_checks(ctx, quiet=True)
            failed = sorted(r["check"] for r in res if not r["ok"])
            hit = any(t in failed for t in targets)
            caught += hit
            results.append({"name": name, "targets": list(targets), "caught": hit, "failed": failed, "note": note})
            print(f"{PREFIX} corruption {'CAUGHT' if hit else 'MISSED'} {list(targets)} {name}"
                  + (f" ({note})" if note else "") + f" (failed: {failed})")
    return caught, total, results


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True, type=Path)
    ap.add_argument("--visuals", required=True, type=Path)
    ap.add_argument("--corruptions", action="store_true")
    ap.add_argument("--write-summary", action="store_true")
    a = ap.parse_args(argv)
    run, vis = a.run.resolve(), a.visuals.resolve()
    res = run_checks(Ctx(run, vis))
    npass = sum(r["ok"] for r in res)
    ok = npass == len(res)
    print(f"{PREFIX} SUMMARY checked={len(res)} failed={len(res) - npass}")
    if ok:
        print(f"{PREFIX} NATURAL_BOOTSTRAP1B_CHECKS_PASS")
    out = {"schema": "NB1b-check-summary-v1", "checks": res, "passed": ok, "code": git("rev-parse", "HEAD").strip()}
    if a.corruptions:
        caught, total, results = corruption_suite(run, vis)
        out["corruptions"] = {"caught": caught, "total": total, "baseline_passing": ok, "results": results}
        print(f"{PREFIX} CORRUPTIONS caught={caught}/{total}" + ("" if ok else " (NOT PROBATIVE: baseline failing)"))
        if ok and caught == total:
            print(f"{PREFIX} NATURAL_BOOTSTRAP1B_MUTATIONS_CAUGHT")
        ok = ok and caught == total
    if a.write_summary:
        (run / "check-summary.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
