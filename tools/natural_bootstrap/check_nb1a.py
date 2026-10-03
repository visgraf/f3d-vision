"""Natural Bootstrap-1a: fail-capable checks of spherical range connectivity.

    .venv/bin/python tools/natural_bootstrap/check_nb1a.py --run RUN --visuals VIS [--corruptions] [--write-summary]

Contract: docs/natural-bootstrap/nb1a-range-connectivity-contract.md, section 10 (checks 1-33).  The
checker recomputes independently, keeping its own literal constants:
- it reads the canonical EXR with the ``OpenEXR`` package (the run uses ``exr_lite``);
- it enumerates all 8 neighbours of every cell and de-duplicates them;
- it computes angular separation with the chord formula 2 asin(|d_i - d_j| / 2);
- it builds components by breadth-first search;
- it computes clearance by vectorized Bellman-Ford relaxation;
- it counts overlaps itself.

``--corruptions`` plants defects in throwaway mirrors (JSON copied, other files linked) or as in-process
mutants.  They count only when the uncorrupted baseline passes.  ``--write-summary`` writes only
``check-summary.json``.
"""
from __future__ import annotations

import argparse
import ast
import collections
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
PREFIX = "[nb1a-check]"

# ---- literal copies (contract sections 2-8); deliberately not imported from nb1a_spec
W, H = 720, 360
N = W * H
SLANT_DEG = 75.0
C_MAX = 1.0 / math.cos(math.radians(75.0))
TIE_EPS = 1e-12
NEIGHBOR_PAIRS_TOTAL = 1_034_640
BASE = "0fe83af8c28c99b6e533972c7b2ec72a8a93b489"
SHARED = Path("/home/lvelho/rd/f3d-vision")
EXR = SHARED / "previews/breadth-1-classroom-234-spherical-glance/render/canonical.exr"
EXR_SHA = "4ea036fc74eab3b3ab06a0c4470c2b01740c9322de0eea522f957ddfffa172f8"
RENDER_PATH = SHARED / "previews/breadth-1-classroom-234-spherical-glance/render"
RENDER_DIR = {"canonical.exr": "4ea036fc74eab3b3ab06a0c4470c2b01740c9322de0eea522f957ddfffa172f8",
              "render-metadata.json": "7c05b80d2d0291f8e12c0886008957b2579e27561b78a766e156b29ec2282157"}
SEEDS = SHARED / "previews/controller-01-full/bootstrap/seeds.json"
SEEDS_SHA = "6ef833196de2462370ba4b2a2a8eed3fbde7f0a61e5aa6cbaf95f66947134c4f"
CATALOG = SHARED / "previews/controller-01-full/bootstrap/instance_catalog.json"
B1_SUMMARY = SHARED / "previews/breadth-1-classroom-234-spherical-glance/summary.json"
FROZEN = ["../input/range-sensory.npz", "continuity-edges.npz", "hypothesis-raster.npz", "hypotheses.json",
          "hypotheses.csv", "seeds.json", "discovery-summary.json", "discovery-opened-files.json"]
DISCOVERY_CODE = ["nb1a_spec.py", "nb1a_discovery.py", "nb1a_guard.py"]
NB1A_FILES = {"docs/natural-bootstrap/nb1a-range-connectivity-contract.md",
              "docs/natural-bootstrap/nb1a-range-connectivity-report.md",
              "tools/repository/check_repository_layout.py"} | {
    f"tools/natural_bootstrap/{n}" for n in ("nb1a_spec.py", "nb1a_guard.py", "nb1a_discovery.py", "nb1a_run.py",
                                             "nb1a_visuals.py", "check_nb1a.py")}
COMMANDS = {"synthetic", "prepare-input", "discover", "freeze", "evaluate", "visualize"}
FORBIDDEN_IMPORTS = re.compile(r"^(fov3d\.control|fov3d\.experiments\.classroom_oracle\.controller|classroom_oracle1_run|"
                               r"classroom_oracle1_matcher|classroom_oracle1_epistemic|classroom_oracle1_eval|"
                               r"multiobject2c_policy|fsg6f|fsg3_surface_map|fsg_stereo|controller0|bpy)")
DISCOVERY_IMPORTS = {"__future__", "heapq", "math", "numpy", "nb1a_spec", "pathlib"}
FIGURES = ["overview.png", "range-input.png", "continuity-boundaries.png", "hypothesis-panorama.png",
           "seed-panorama.png", "hypothesis-support-histogram.png", "interior-clearance-histogram.png",
           "overlap-matrix.png", "rgb-edge-contrast.png"]
FORBIDDEN_INPUT_KEYS = re.compile(r"instance|object.?index|catalog|object_name|accepted|seed|label|component|oracle",
                                  re.IGNORECASE)
_CACHE: dict = {}


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git(*args) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout


# ------------------------------------------------------------------ independent geometry and graph
def directions() -> np.ndarray:
    lon = np.radians(-180.0 + 0.5 * (np.arange(W) + 0.5))
    lat = np.radians(90.0 - 0.5 * (np.arange(H) + 0.5))
    x = np.outer(np.cos(lat), np.sin(lon)); y = np.repeat(np.sin(lat)[:, None], W, 1); z = -np.outer(np.cos(lat), np.cos(lon))
    return np.stack([x, y, z], -1).reshape(-1, 3)


def all_pairs() -> np.ndarray:
    """Every unordered 8-neighbour pair (longitude wraps, latitude does not) as sorted keys a*N + b, a < b."""
    if "pairs" in _CACHE:
        return _CACHE["pairs"]
    r, c = np.divmod(np.arange(N), W)
    keys = []
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            r2 = r + dr
            ok = (r2 >= 0) & (r2 < H)
            b = r2[ok] * W + (c[ok] + dc) % W
            a = np.arange(N)[ok]
            keys.append(np.minimum(a, b) * N + np.maximum(a, b))
    out = np.unique(np.concatenate(keys))
    _CACHE["pairs"] = out
    return out


def fold_support(rows: np.ndarray) -> float:
    """The contract's canonical support: folded mirror rows, math.sin, math.fsum (literal re-implementation)."""
    n = np.bincount(rows, minlength=H)
    m = n[:H // 2] + n[::-1][:H // 2]
    ds = [math.sin(math.pi / 2 - k * math.pi / H) - math.sin(math.pi / 2 - (k + 1) * math.pi / H) for k in range(H // 2)]
    return (2 * math.pi / W) * math.fsum(int(a) * b for a, b in zip(m.tolist(), ds) if a)


def weights_cos() -> np.ndarray:
    phi = math.pi / 2 - (np.arange(H) + 0.5) * math.pi / H
    return 2.0 * (2 * math.pi / W) * np.cos(phi) * math.sin(math.pi / H / 2)


def graph(rng: np.ndarray, valid: np.ndarray) -> dict:
    """Candidate pairs, chord-formula delta, C and retained state, recomputed independently."""
    key = ("graph", hashlib.sha256(rng.tobytes() + valid.tobytes()).hexdigest())
    if key in _CACHE:
        return _CACHE[key]
    k = all_pairs()
    a, b = k // N, k % N
    v = valid.reshape(-1)
    cand = v[a] & v[b]
    a, b = a[cand], b[cand]
    d = directions()
    delta = 2.0 * np.arcsin(np.linalg.norm(d[a] - d[b], axis=1) / 2.0)
    r = rng.reshape(-1)
    g = np.linalg.norm(r[a][:, None] * d[a] - r[b][:, None] * d[b], axis=1)
    c = g / (0.5 * (r[a] + r[b]) * delta)
    out = {"a": a, "b": b, "key": a * N + b, "delta": delta, "C": c, "retained": c <= C_MAX}
    _CACHE[key] = out
    return out


def bfs_components(valid: np.ndarray, a: np.ndarray, b: np.ndarray, keep: np.ndarray) -> np.ndarray:
    adj = collections.defaultdict(list)
    for x, y in zip(a[keep].tolist(), b[keep].tolist()):
        adj[x].append(y); adj[y].append(x)
    comp = np.full(N, -1, np.int64)
    nxt = 0
    for s in np.flatnonzero(valid.reshape(-1)).tolist():
        if comp[s] >= 0:
            continue
        comp[s] = nxt
        q = collections.deque([s])
        while q:
            u = q.popleft()
            for w_ in adj.get(u, ()):
                if comp[w_] < 0:
                    comp[w_] = nxt
                    q.append(w_)
        nxt += 1
    return comp


def boundary_of(labels_flat: np.ndarray, valid: np.ndarray) -> np.ndarray:
    v = valid.reshape(-1)
    k = all_pairs()
    a, b = k // N, k % N
    differ = ~v[a] | ~v[b] | (labels_flat[a] != labels_flat[b])
    bnd = np.zeros(N, bool)
    bnd[a[differ & v[a]]] = True
    bnd[b[differ & v[b]]] = True
    return bnd


def bellman_ford(bnd: np.ndarray, valid: np.ndarray, a, b, delta, keep) -> np.ndarray:
    dist = np.where(bnd, 0.0, np.inf)
    src = np.concatenate([a[keep], b[keep]]); dst = np.concatenate([b[keep], a[keep]]); w_ = np.concatenate([delta[keep]] * 2)
    while True:
        cand = dist[src] + w_
        new = dist.copy()
        np.minimum.at(new, dst, cand)
        if np.array_equal(new, dist):
            break
        dist = new
    dist[~valid.reshape(-1)] = np.nan
    return dist


def seed_rule(member: np.ndarray, dist: np.ndarray) -> tuple[int, float | None, str | None, int | None]:
    if len(member) == 1:
        return int(member[0]), 0.0, None, 1
    dd = dist[member]
    if np.all(np.isinf(dd)):
        return int(member.min()), None, "NO_BOUNDARY_FALLBACK", None
    mx = float(dd.max())
    tied = member[mx - dd <= TIE_EPS]
    return int(tied.min()), mx, None, int(len(tied))


def solve(rng: np.ndarray, valid: np.ndarray) -> dict:
    """The whole independent discovery: graph, components, ordering, boundary, clearance, seeds."""
    key = ("solve", hashlib.sha256(rng.tobytes() + valid.tobytes()).hexdigest())
    if key in _CACHE:
        return _CACHE[key]
    gph = graph(rng, valid)
    comp = bfs_components(valid, gph["a"], gph["b"], gph["retained"])
    groups = collections.defaultdict(list)
    for cell in np.flatnonzero(comp >= 0).tolist():
        groups[int(comp[cell])].append(cell)
    recs = []
    for cells in groups.values():
        m = np.array(sorted(cells))
        recs.append({"cells_flat": m, "cells": len(m), "support": fold_support(m // W), "min": int(m[0])})
    recs.sort(key=lambda r: (-r["support"], -r["cells"], r["min"]))
    labels = np.zeros(N, np.int64)
    for k, r in enumerate(recs, start=1):
        labels[r["cells_flat"]] = k
    bnd = boundary_of(labels, valid)
    dist = bellman_ford(bnd, valid, gph["a"], gph["b"], gph["delta"], gph["retained"])
    for r in recs:
        r["seed"] = seed_rule(r["cells_flat"], dist)
    out = {"graph": gph, "labels": labels, "recs": recs, "boundary": bnd, "dist": dist}
    _CACHE[key] = out
    return out


# ------------------------------------------------------------------ context
class Ctx:
    def __init__(self, run: Path, vis: Path):
        self.run, self.vis = Path(run), Path(vis)
        j = lambda p: json.loads((self.run / p).read_text())  # noqa: E731
        self.inman = j("input/input-manifest.json")
        self.inopen = j("input/input-opened-files.json")
        self.hyps_doc = j("discovery/hypotheses.json")
        self.hyps = self.hyps_doc["hypotheses"]
        self.seeds = j("discovery/seeds.json")["seeds"]
        self.summ = j("discovery/discovery-summary.json")
        self.dopen = j("discovery/discovery-opened-files.json")
        self.freeze = j("discovery/bootstrap-freeze.json")
        self.ov = j("evaluation/overlap-summary.json")
        self.rgbd = j("evaluation/rgb-edge-diagnostics.json")
        self.eopen = j("evaluation/evaluation-opened-files.json")
        self.synthetic = j("synthetic/synthetic-report.json")
        self.manifest = j("manifest.json")
        self.processes = [json.loads(l) for l in (self.run / "process-log.jsonl").read_text().splitlines() if l.strip()]
        self.vman = json.loads((self.vis / "visuals-manifest.json").read_text())
        self.rs = dict(np.load(self.run / "input/range-sensory.npz"))
        self.rgb_in = dict(np.load(self.run / "input/rgb-sensory.npz"))
        self.edges = dict(np.load(self.run / "discovery/continuity-edges.npz"))
        self.raster = dict(np.load(self.run / "discovery/hypothesis-raster.npz"))
        self.ovm = dict(np.load(self.run / "evaluation/overlap-matrix.npz"))
        self.rgbc = dict(np.load(self.run / "evaluation/rgb-edge-contrast.npz"))
        self.refc = dict(np.load(self.run / "evaluation/reference-cells.npz"))
        self.exr_path = EXR
        self.changed_files = None
        self.fov3d_changed = None

    def exr(self) -> dict:
        key = ("exr", sha256(self.exr_path))
        if key not in _CACHE:
            import OpenEXR
            with OpenEXR.File(str(self.exr_path), separate_channels=True) as f:
                window = tuple(np.array(v).tolist() for v in f.header()["dataWindow"])
                ch = {k: np.array(v.pixels) for k, v in f.channels().items()}
            pick = lambda s: next(v for k, v in ch.items() if k.endswith(s))  # noqa: E731
            _CACHE[key] = {"window": window, "pos": np.stack([pick(f"Position.{c}") for c in "XYZ"], -1).astype(np.float32),
                           "rgb": np.stack([pick(f"Combined.{c}") for c in "RGB"], -1).astype(np.float32),
                           "oid": np.rint(pick("Object Index.X")).astype(np.int64)}
        return _CACHE[key]

    def proxy(self) -> tuple[np.ndarray, np.ndarray]:
        e = self.exr()
        o = np.asarray(json.loads(SEEDS.read_text())["head_origin_w_m"], np.float64)
        valid = ~np.all(e["pos"] == 0, axis=-1)
        rng = np.zeros(valid.shape)
        dd = e["pos"].astype(np.float64) - o
        rng[valid] = np.sqrt((dd[valid] ** 2).sum(-1))
        return rng, valid

    def solved(self) -> dict:
        return solve(self.rs["range_m"], self.rs["valid_mask"])


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


# ------------------------------------------------------------------ checks
def c01(ctx):
    return sha256(ctx.exr_path) == EXR_SHA and ctx.inman["sources"]["canonical_exr"]["sha256"] == EXR_SHA, \
        f"canonical EXR {sha256(ctx.exr_path)[:12]}"


def c02(ctx):
    bad = [p["command"] for p in ctx.processes if any("blender" in str(a).lower() for a in p["argv"])]
    rd = RENDER_PATH
    files = sorted(p.name for p in rd.iterdir())
    same = files == ["blender.log", "canonical.exr", "render-metadata.json"] and all(
        sha256(rd / n) == h for n, h in RENDER_DIR.items())
    return not bad and same, f"Blender in process log: {bad}; Breadth-1 render directory unchanged: {same}"


def c03(ctx):
    r, v, s = ctx.rs["range_m"], ctx.rs["valid_mask"], ctx.rgb_in["srgb8"]
    ok = r.shape == (H, W) and v.shape == (H, W) and s.shape == (H, W, 3) and ctx.exr()["window"] == ([0, 0], [W - 1, H - 1])
    return ok, f"range {r.shape}, rgb {s.shape}, EXR window {ctx.exr()['window']}"


def c04(ctx):
    rng, valid = ctx.proxy()
    ok = np.array_equal(valid, ctx.rs["valid_mask"]) and float(np.max(np.abs(rng - ctx.rs["range_m"]))) <= 1e-9
    e = ctx.exr()
    lin = np.clip(e["rgb"].astype(np.float64), 0, 1)
    s8 = np.rint(np.where(lin <= 0.0031308, 12.92 * lin, 1.055 * lin ** (1 / 2.4) - 0.055) * 255).astype(np.uint8)
    rgb_ok = np.array_equal(s8, ctx.rgb_in["srgb8"])
    return ok and rgb_ok, f"valid equal {np.array_equal(valid, ctx.rs['valid_mask'])}; max |range diff| " \
                          f"{float(np.max(np.abs(rng - ctx.rs['range_m']))):.2g}; sRGB proxy equal {rgb_ok}"


def c05(ctx):
    bad = []
    if sorted(ctx.rs) != ["range_m", "valid_mask"]:
        bad.append(f"range input arrays {sorted(ctx.rs)}")
    if sorted(ctx.rgb_in) != ["srgb8"]:
        bad.append(f"rgb input arrays {sorted(ctx.rgb_in)}")
    if ctx.rs["range_m"].dtype != np.float64 or ctx.rs["valid_mask"].dtype != bool:
        bad.append("dtypes")

    def walk(x, path=""):
        if isinstance(x, dict):
            for k, v in x.items():
                if FORBIDDEN_INPUT_KEYS.search(str(k)):
                    bad.append(f"manifest key {path}.{k}")
                walk(v, f"{path}.{k}")
        elif isinstance(x, list) and len(x) > 50:
            bad.append(f"long list at {path}")
    walk({k: v for k, v in ctx.inman.items() if k not in ("sources",)})
    used = ctx.inman["sources"]["canonical_exr"]["channels_used"]
    if any("Index" in u for u in used) or ctx.inman["sources"]["head_pose"]["fields_used"] != ["head_origin_w_m"]:
        bad.append("declared channel / field use")
    return not bad, f"violations {bad[:4]}"


def _reads(rec):
    return [e for e in rec["events"] if e.get("kind") in ("data-read", "own-output-read")]


def _root(rec, leaf: str) -> Path | None:
    """The run root the guard declared (its single write directory must be <root>/<leaf>)."""
    dirs = rec.get("allow_write_dirs", [])
    return Path(dirs[0]).parent if len(dirs) == 1 and Path(dirs[0]).name == leaf else None


def c06(ctx):
    rd = ctx.dopen
    root = _root(rd, "discovery")
    if root is None or root.name != ctx.run.name:
        return False, f"discovery guard write directories {rd.get('allow_write_dirs')}"
    src = str(root / "input/range-sensory.npz")
    dreads = {e["path"] for e in rd["events"] if e.get("kind") == "data-read"}
    writes = {e["path"] for e in rd["events"] if e.get("kind") == "write"}
    out = str(root / "discovery")
    ok = (dreads == {src} and set(rd.get("allow_read", [])) == {src} and all(p.startswith(out + "/") for p in writes)
          and not rd["violations"]
          and rd.get("truth_firewall_violations") == 0 and all(e.get("allowed", True) for e in rd["events"]))
    sys.path.insert(0, str(HERE))
    from nb1a_guard import OpenGuard
    blocked = False
    try:
        with OpenGuard("self-test", [src], [out]):
            open(ctx.run / "input/rgb-sensory.npz", "rb").close()
    except PermissionError:
        blocked = True
    return ok and blocked, f"data reads {sorted(Path(p).name for p in dreads)}; writes {len(writes)}; violations " \
                           f"{len(rd['violations'])}; guard self-test blocks RGB {blocked}"


def c07(ctx):
    hit = [e["path"] for e in ctx.dopen["events"] if "rgb" in Path(e.get("path", "")).name.lower()]
    return not hit, f"RGB opens during discovery: {hit}"


def c08(ctx):
    forb = [str(EXR), str(CATALOG), str(B1_SUMMARY), str(SEEDS)]
    hit = [e["path"] for e in ctx.dopen["events"] if e.get("path") in forb or "/evaluation/" in e.get("path", "")
           or e.get("path", "").endswith((".exr",)) or "controller-0" in e.get("path", "")]
    bad_imports = []
    for f in ("nb1a_discovery.py", "nb1a_spec.py"):
        for node in ast.walk(ast.parse((HERE / f).read_text())):
            mods = [a.name for a in node.names] if isinstance(node, ast.Import) else (
                [node.module or ""] if isinstance(node, ast.ImportFrom) else [])
            bad_imports += [f"{f}:{m}" for m in mods if m.split(".")[0] not in DISCOVERY_IMPORTS]
    return not hit and not bad_imports, f"forbidden opens {hit[:3]}; non-declared discovery imports {bad_imports}"


def c09(ctx):
    sys.path.insert(0, str(HERE))
    import nb1a_spec as SP
    return bool(np.allclose(SP.cell_directions_h().reshape(-1, 3), directions(), atol=1e-14)), "cell directions"


def c10(ctx):
    g = ctx.solved()["graph"]
    a, b = ctx.edges["a"].astype(np.int64), ctx.edges["b"].astype(np.int64)
    key = np.sort(np.minimum(a, b) * N + np.maximum(a, b))
    ok = np.array_equal(key, np.sort(g["key"])) and len(all_pairs()) == NEIGHBOR_PAIRS_TOTAL \
        and ctx.summ["neighbor_pairs_total"] == NEIGHBOR_PAIRS_TOTAL and ctx.summ["candidate_pairs"] == len(g["key"])
    return ok, f"{len(all_pairs()):,} neighbour pairs; candidates stored {len(key):,} vs recomputed {len(g['key']):,}"


def _align(ctx):
    """Map stored edge rows onto the checker's recomputed rows (by unordered key)."""
    g = ctx.solved()["graph"]
    a, b = ctx.edges["a"].astype(np.int64), ctx.edges["b"].astype(np.int64)
    key = np.minimum(a, b) * N + np.maximum(a, b)
    idx = np.searchsorted(g["key"], key)
    idx = np.clip(idx, 0, len(g["key"]) - 1)
    if not np.array_equal(g["key"][idx], key):
        return None, g
    return idx, g


def c11(ctx):
    idx, g = _align(ctx)
    if idx is None:
        return False, "edge sets differ"
    diff = float(np.max(np.abs(ctx.edges["delta"] - g["delta"][idx])))
    return diff <= 1e-14, f"max |delta - chord formula| {diff:.2g} rad"


def c12(ctx):
    idx, g = _align(ctx)
    if idx is None:
        return False, "edge sets differ"
    rel = float(np.max(np.abs(ctx.edges["C"] / g["C"][idx] - 1)))
    return rel <= 1e-9, f"max relative |C - independent C| {rel:.2g}"


def c13(ctx):
    cfgs = [ctx.hyps_doc["config"], ctx.freeze["discovery_config"]]
    ok = all(c["MAX_SURFACE_SLANT_DEG"] == SLANT_DEG and c["C_MAX"] == C_MAX for c in cfgs) \
        and ctx.summ["C_MAX"] == C_MAX and ctx.summ["MAX_SURFACE_SLANT_DEG"] == SLANT_DEG \
        and abs(C_MAX - 3.863703305156273) < 1e-12
    return ok, f"C_MAX {C_MAX!r} = sec 75 deg; declared {[c['MAX_SURFACE_SLANT_DEG'] for c in cfgs]}"


def c14(ctx):
    idx, g = _align(ctx)
    if idx is None:
        return False, "edge sets differ"
    mism = int((ctx.edges["retained"] != g["retained"][idx]).sum())
    ok = mism == 0 and ctx.summ["retained_edges"] == int(g["retained"].sum()) and ctx.summ["cut_edges"] == int((~g["retained"]).sum())
    return ok, f"edge-state mismatches {mism}; retained {int(g['retained'].sum()):,}, cut {int((~g['retained']).sum()):,}"


def c15(ctx):
    s = ctx.solved()
    lab = ctx.raster["labels"].reshape(-1).astype(np.int64)
    v = ctx.rs["valid_mask"].reshape(-1)
    pairs = set(zip(s["labels"][v].tolist(), lab[v].tolist()))
    ok = len(pairs) == len(s["recs"]) == len({p[1] for p in pairs}) == len({p[0] for p in pairs})
    return ok, f"independent components {len(s['recs']):,}; stored labels {len(set(lab[v].tolist())):,}; 1:1 {ok}"


def c16(ctx):
    lab = ctx.raster["labels"].reshape(-1)
    v = ctx.rs["valid_mask"].reshape(-1)
    ids = {h["label"] for h in ctx.hyps}
    ok = bool(np.all(lab[v] > 0)) and set(np.unique(lab[v]).tolist()) == ids and len(ids) == len(ctx.hyps) \
        and sum(h["cells"] for h in ctx.hyps) == int(v.sum())
    return ok, f"valid cells {int(v.sum()):,}; unlabelled valid {int((lab[v] <= 0).sum())}; records {len(ctx.hyps):,}"


def c17(ctx):
    lab = ctx.raster["labels"].reshape(-1)
    v = ctx.rs["valid_mask"].reshape(-1)
    return bool(np.all(lab[~v] == 0)), f"labelled invalid cells {int((lab[~v] != 0).sum())}"


def c18(ctx):
    s = ctx.solved()
    sizes_c = sorted(r["cells"] for r in s["recs"])
    sizes_s = sorted(h["cells"] for h in ctx.hyps)
    ok = sizes_c == sizes_s and ctx.summ["hypotheses"] == len(s["recs"]) and \
        ctx.summ["singletons"] == sum(1 for r in s["recs"] if r["cells"] == 1)
    return ok, f"component sizes equal {sizes_c == sizes_s}; count {len(s['recs']):,} vs {len(ctx.hyps):,}"


def c19(ctx):
    s = ctx.solved()
    lab = ctx.raster["labels"].reshape(-1).astype(np.int64)
    ok = np.array_equal(lab, s["labels"])
    ids_ok = all(h["id"] == f"H{k:04d}" and h["label"] == k for k, h in enumerate(ctx.hyps, start=1))
    sup_ok = all(abs(h["support_sr"] - r["support"]) == 0.0 for h, r in zip(ctx.hyps, s["recs"]))
    wc = weights_cos()
    cos_ok = all(abs(r["support"] - float(np.bincount(r["cells_flat"] // W, minlength=H) @ wc)) <= 1e-12 * max(r["support"], 1e-300)
                 + 1e-18 for r in s["recs"][:2000])
    return ok and ids_ok and sup_ok and cos_ok, f"ordering/labels equal {ok}; ids {ids_ok}; support exact {sup_ok}; cos-weight agreement {cos_ok}"


def c20(ctx):
    s = ctx.solved()
    stored = ctx.raster["boundary"].reshape(-1)
    ok = np.array_equal(stored, s["boundary"])
    cnt = all(h["boundary_cells"] == int(s["boundary"][r["cells_flat"]].sum()) for h, r in zip(ctx.hyps, s["recs"]))
    return ok and cnt, f"boundary raster equal {ok}; per-hypothesis counts {cnt}"


def c21(ctx):
    s = ctx.solved()
    a, b = ctx.raster["clearance_rad"].reshape(-1), s["dist"]
    same_nan = np.array_equal(np.isnan(a), np.isnan(b)) and np.array_equal(np.isinf(a), np.isinf(b))
    fin = np.isfinite(a) & np.isfinite(b)
    diff = float(np.max(np.abs(a[fin] - b[fin]))) if fin.any() else 0.0
    return same_nan and diff <= 1e-12, f"max |clearance diff| {diff:.2g} rad; nan/inf pattern equal {same_nan}"


def c22(ctx):
    s = ctx.solved()
    lab = ctx.raster["labels"].reshape(-1)
    bad = []
    for h, sd, r in zip(ctx.hyps, ctx.seeds, s["recs"]):
        flat = sd["row"] * W + sd["col"]
        want, mx, fb, _t = r["seed"]
        if lab[flat] != h["label"] or sd["id"] != h["id"] or (sd["row"], sd["col"]) != (h["seed"]["row"], h["seed"]["col"]):
            bad.append((h["id"], "not on its hypothesis"))
            continue
        if fb is None:
            dv = s["dist"][flat]
            if not (mx - dv <= TIE_EPS) or abs((h["seed"]["clearance_rad"] or 0.0) - mx) > 1e-12:
                bad.append((h["id"], "not max clearance"))
    return not bad and len(ctx.seeds) == len(ctx.hyps), f"{len(ctx.seeds):,} seeds; wrong {bad[:3]}"


def c23(ctx):
    s = ctx.solved()
    bad = []
    for h, r in zip(ctx.hyps, s["recs"]):
        want, mx, fb, tied = r["seed"]
        sd = h["seed"]
        if (sd["row"] * W + sd["col"] != want or sd["fallback"] != fb or sd["tied_candidates"] != tied
                or (h["cells"] == 1 and sd["clearance_rad"] != 0.0)):
            bad.append(h["id"])
    nfb = sum(1 for r in s["recs"] if r["seed"][2])
    ok = not bad and ctx.summ["no_boundary_fallbacks"] == nfb and \
        ctx.summ["zero_clearance_seeds"] == sum(1 for r in s["recs"] if r["seed"][1] == 0.0) and \
        ctx.summ["tied_seed_hypotheses"] == sum(1 for r in s["recs"] if (r["seed"][3] or 0) > 1)
    return ok, f"rule violations {bad[:4]}; ties {sum(1 for r in s['recs'] if (r['seed'][3] or 0) > 1)}; fallbacks {nfb}"


def c24(ctx):
    d = ctx.run / "discovery"
    hashes_ok = set(ctx.freeze["files"]) == set(FROZEN) and all(sha256(d / n) == h for n, h in ctx.freeze["files"].items())
    code_ok = all(sha256(HERE / n) == h for n, h in ctx.freeze["discovery_code"].items())
    order = ctx.eopen.get("ordered_data_events", [])
    root = _root(ctx.eopen, "evaluation") or ctx.run
    ref = {str(EXR), str(CATALOG), str(B1_SUMMARY), str(root / "input/rgb-sensory.npz")}
    try:
        k = order.index("freeze_verified")
        ok_order = not any(o in ref for o in order[:k]) and any(o in ref for o in order[k:]) \
            and "reference_access_begins" in order[k:]
    except ValueError:
        ok_order = False
    return hashes_ok and code_ok and ok_order, f"freeze hashes {hashes_ok}; discovery code {code_ok}; reference only after verification {ok_order}"


def c25(ctx):
    root = _root(ctx.eopen, "evaluation")
    writes = {e["path"] for e in ctx.eopen["events"] if e.get("kind") == "write"}
    out = str(root / "evaluation") if root else "\0"
    ok = root is not None and root.name == ctx.run.name and all(p.startswith(out + "/") for p in writes) \
        and bool(writes) and not ctx.eopen["violations"]
    still = all(sha256(ctx.run / "discovery" / n) == h for n, h in ctx.freeze["files"].items())
    return ok and still, f"evaluation writes only under evaluation/ {ok}; frozen products unchanged {still}"


def c26(ctx):
    lab = ctx.raster["labels"].reshape(-1).astype(np.int64)
    oid = ctx.exr()["oid"].reshape(-1)
    cells = np.flatnonzero(lab > 0)
    pairs = collections.Counter(zip(lab[cells].tolist(), oid[cells].tolist()))
    stored = {(int(h), int(o)): int(c) for h, o, c in zip(ctx.ovm["h"], ctx.ovm["o"], ctx.ovm["cells"])}
    ok = stored == dict(pairs)
    sr_ok = True
    if ok:
        rows_by = collections.defaultdict(list)
        for c in cells.tolist():
            rows_by[(int(lab[c]), int(oid[c]))].append(c // W)
        wc = weights_cos()
        for (h, o), sr in zip(zip(ctx.ovm["h"].tolist(), ctx.ovm["o"].tolist()), ctx.ovm["support_sr"].tolist()):
            ref = float(np.bincount(np.array(rows_by[(h, o)]), minlength=H) @ wc)
            if abs(sr - ref) > 1e-12 * max(ref, 1e-300) + 1e-18:
                sr_ok = False
                break
    return ok and sr_ok, f"{len(stored):,} stored pairs vs {len(pairs):,} recomputed; cells equal {ok}; sr agree {sr_ok}"


def c27(ctx):
    oid = ctx.exr()["oid"]
    v = ctx.rs["valid_mask"]
    o0 = int((v & (oid == 0)).sum())
    st = int(ctx.ovm["cells"][ctx.ovm["o"] == 0].sum())
    b1 = json.loads(B1_SUMMARY.read_text())["cell_accounting"]
    a = ctx.ov["accounting"]
    ok = (o0 == st == a["O0_cells"] and o0 > 0 and a["O0_cells"] == b1["index0_noncatalog_geometry"]["cells"]
          and a["catalog_cells"] == b1["authored"]["cells"] and a["matches_breadth1"] is True
          and np.array_equal(ctx.refc["o0_mask"], (ctx.raster["labels"] > 0) & (oid == 0))
          and np.array_equal(ctx.refc["object_index"].astype(np.int64), oid))
    return ok, f"O_0 cells {o0:,} (stored {st:,}; Breadth-1 {b1['index0_noncatalog_geometry']['cells']:,})"


def c28(ctx):
    s8 = ctx.rgb_in["srgb8"].reshape(-1, 3).astype(np.float64) / 255.0
    lin = np.where(s8 <= 0.04045, s8 / 12.92, ((s8 + 0.055) / 1.055) ** 2.4)
    a, b = ctx.edges["a"].astype(np.int64), ctx.edges["b"].astype(np.int64)
    con = np.sqrt(((lin[a] - lin[b]) ** 2).sum(1))
    ok_c = float(np.max(np.abs(con - ctx.rgbc["contrast"]))) <= 1e-12
    ret = ctx.edges["retained"]
    ok_q = abs(ctx.rgbd["retained"]["quantiles"][4] - float(np.median(con[ret]))) <= 1e-12 and \
        ctx.rgbd["cut"]["edges_n"] == int((~ret).sum())
    after = ctx.rgbd.get("computed_after_freeze") is True and ctx.rgbd.get("frozen_inputs_sha256") == ctx.freeze["files"]
    still = all(sha256(ctx.run / "discovery" / n) == h for n, h in ctx.freeze["files"].items())
    return ok_c and ok_q and after and still, f"contrast recomputes {ok_c}; distributions {ok_q}; post-freeze {after}; discovery unchanged {still}"


def c29(ctx):
    sys.path.insert(0, str(HERE))
    import nb1a_visuals as V
    key = ("vis", tuple(sorted((n, sha256(ctx.run / n)) for n in V.Data.SOURCES)))
    if key not in _CACHE:
        figs, _d = V.render_all(ctx.run)
        _CACHE[key] = {n: hashlib.sha256(V.png_bytes(figs[n])).hexdigest() for n in FIGURES}
    want = _CACHE[key]
    bad = [n for n in FIGURES if not (ctx.vis / n).is_file() or sha256(ctx.vis / n) != want[n]
           or ctx.vman["products"][n]["sha256"] != want[n]]
    return not bad, f"{len(FIGURES) - len(bad)}/{len(FIGURES)} figures regenerate byte-identically; differ {bad}"


def c30(ctx):
    ch = fov3d_changed(ctx)
    ctrl = [f for f in changed_files(ctx) if f.startswith(("tools/controller/", "fov3d/")) or f in (
        "tools/classroom_oracle1_render.py", "tools/classroom_oracle1_run.py", "tools/fsg6f_frontier.py")]
    return not ch and not ctrl, f"fov3d changed {ch}; controller files changed {ctrl}"


def c31(ctx):
    extra = [f for f in changed_files(ctx) if f not in NB1A_FILES]
    return not extra, f"undeclared changes vs {BASE[:7]}: {extra[:6]}"


def c32(ctx):
    bad = [p for p in ctx.processes if p["command"] not in COMMANDS
           or not any(str(a).endswith("nb1a_run.py") for a in p["argv"][:1])
           or any(re.search(r"controller0|classroom_oracle1_run|blender", str(a)) for a in p["argv"])]
    imp = []
    for f in sorted(n for n in NB1A_FILES if n.endswith(".py") and "natural_bootstrap" in n):
        for node in ast.walk(ast.parse((REPO / f).read_text())):
            mods = [a.name for a in node.names] if isinstance(node, ast.Import) else (
                [node.module or ""] if isinstance(node, ast.ImportFrom) else [])
            imp += [f"{f}:{m}" for m in mods if FORBIDDEN_IMPORTS.match(m)]
    return not bad and not imp, f"non-NB1a processes {[p['command'] for p in bad][:3]}; forbidden imports {imp}"


def synthetic_cases():
    """The checker's own known-answer shapes (constructed independently of the generator)."""
    d = directions().reshape(H, W, 3)
    cases = []

    def z():
        return np.zeros((H, W)), np.zeros((H, W), bool)
    r, v = z(); r[170:190, 350:370] = 2; v[170:190, 350:370] = True; cases.append(("fronto", r, v, 1, None))
    r, v = z(); r[170:190, 350:360] = 2; r[170:190, 360:370] = 3; v[170:190, 350:370] = True; cases.append(("step", r, v, 2, None))
    for th, want in ((73.5, 1), (76.5, 3)):
        r, v = z()
        d0 = d[180, 360]
        az = math.atan2(d0[0], -d0[2]) + math.radians(th)
        n = np.array([math.sin(az), 0.0, -math.cos(az)])
        for c in (359, 360, 361):
            r[180, c] = 2.0 * float(n @ d0) / float(n @ d[180, c]); v[180, c] = True
        cases.append((f"slant {th}", r, v, want, None))
    r, v = z(); v[175:185, 715:720] = v[175:185, 0:5] = True; r[v] = 2; cases.append(("seam", r, v, 1, None))
    r, v = z(); v[180, 400] = v[181, 401] = True; r[v] = 2; cases.append(("diagonal", r, v, 1, None))
    r, v = z(); v[100, 100] = True; r[v] = 2; cases.append(("singleton", r, v, 1, (100 * W + 100, 0.0, None, 1)))
    r, v = z(); v[170:191, 350:371] = True; r[v] = 2; cases.append(("deep interior", r, v, 1, (180 * W + 360, None, None, 1)))
    r, v = z(); v[170:190, 350:370] = True; r[v] = 2; cases.append(("four-way tie", r, v, 1, (179 * W + 359, None, None, 4)))
    r = np.full((H, W), 2.0); v = np.ones((H, W), bool); cases.append(("no boundary", r, v, 1, (0, None, "NO_BOUNDARY_FALLBACK", None)))
    return cases


def c33(ctx):
    gen = ctx.synthetic
    gen_ok = gen["passed"] and len(gen["cases"]) >= 10 and all(c["ok"] for c in gen["cases"])
    bad = []
    for name, r, v, nh, sd in synthetic_cases():
        s = solve(r, v)
        if len(s["recs"]) != nh:
            bad.append(name)
            continue
        if sd is not None:
            got = s["recs"][0]["seed"]
            if got[0] != sd[0] or got[2] != sd[2] or got[3] != sd[3] or (sd[1] is not None and got[1] != sd[1]):
                bad.append(f"{name} seed {got}")
    return gen_ok and not bad, f"generator report {gen_ok}; independent known-answer failures {bad}"


CHECKS = [(f"{i:02d}", name, fn) for i, (name, fn) in enumerate([
    ("source canonical EXR hash is exactly accepted", c01), ("no Blender invocation occurred", c02),
    ("sensory input is exactly 720 x 360", c03), ("range and validity recompute from Position", c04),
    ("stripped inputs hold no identity / catalog data", c05), ("discovery opened only allowed files", c06),
    ("discovery did not open RGB", c07), ("discovery did not open Object Index / catalog / evaluation", c08),
    ("spherical cell directions recompute", c09), ("seam-aware 8-neighbour enumeration recomputes", c10),
    ("true angular separations recompute", c11), ("C_ij recomputes independently", c12),
    ("C_MAX equals sec 75 deg", c13), ("retained / cut edge states recompute exactly", c14),
    ("connected components recompute independently", c15), ("every valid cell belongs to exactly one hypothesis", c16),
    ("no invalid cell belongs to a hypothesis", c17), ("no component filtered, merged or deleted", c18),
    ("deterministic ordering and ids recompute", c19), ("boundary cells recompute", c20),
    ("interior clearance recomputes (Bellman-Ford)", c21), ("seeds lie in their hypothesis at maximum clearance", c22),
    ("seed tie / singleton / fallback behaviour", c23), ("freeze verified before reference access", c24),
    ("evaluation did not alter bootstrap products", c25), ("overlap matrix recomputes", c26),
    ("O_0 included; accounting matches Breadth-1", c27), ("RGB diagnostics post-freeze, recompute, no effect", c28),
    ("visual products regenerate deterministically", c29), ("fov3d / accepted controllers unchanged", c30),
    ("changed files are declared NB1a files only", c31), ("no controller executed", c32),
    ("synthetic known-answer shapes (generator and independent)", c33)], start=1)]


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
    z = dict(np.load(path)); fn(z); path.unlink(); np.savez_compressed(path, **z)


def refreeze(m: Path, names=None) -> None:
    """Re-hash the named products into the mirror's freeze, so that only the targeted check can object."""
    def fn(d):
        for n in (names or d["files"]):
            d["files"][n] = sha256(m / "discovery" / n)
    edit_json(m / "discovery/bootstrap-freeze.json", fn)


def regenerate(m: Path, **variant) -> None:
    sys.path.insert(0, str(HERE))
    import nb1a_discovery as D
    import nb1a_run as R
    with np.load(m / "input/range-sensory.npz") as z:
        rng, valid = z["range_m"], z["valid_mask"]
    res = D.discover(rng, valid, **variant)
    for n in ("continuity-edges.npz", "hypothesis-raster.npz", "hypotheses.json", "hypotheses.csv", "seeds.json"):
        (m / "discovery" / n).unlink()
    R.write_discovery(m / "discovery", res, valid)
    refreeze(m)


def corruptions():
    def flip_edge(m, v, c):
        edit_npz(m / "discovery/continuity-edges.npz", lambda z: z["retained"].__setitem__(0, ~z["retained"][0]))
        refreeze(m, ["continuity-edges.npz"])

    def slant(m, v, c):
        for p in ("discovery/hypotheses.json",):
            edit_json(m / p, lambda d: d["config"].update(MAX_SURFACE_SLANT_DEG=70.0, C_MAX=1 / math.cos(math.radians(70))))
        edit_json(m / "discovery/bootstrap-freeze.json", lambda d: d["discovery_config"].update(
            MAX_SURFACE_SLANT_DEG=70.0, C_MAX=1 / math.cos(math.radians(70))))
        refreeze(m, ["hypotheses.json"])

    def label(m, v, c):
        big = c.hyps[0]["label"]
        def fn(z):
            lab = z["labels"].copy(); cells = np.flatnonzero(lab.reshape(-1) == big)
            lab.reshape(-1)[cells[len(cells) // 2]] = c.hyps[1]["label"] if len(c.hyps) > 1 else big + 1
            z["labels"] = lab
        edit_npz(m / "discovery/hypothesis-raster.npz", fn); refreeze(m, ["hypothesis-raster.npz"])

    def del_singleton(m, v, c):
        s = [h for h in c.hyps if h["cells"] == 1]
        if not s:
            return {"not_applicable": "no singleton hypothesis"}
        L = s[-1]["label"]
        edit_npz(m / "discovery/hypothesis-raster.npz", lambda z: z.__setitem__("labels", np.where(z["labels"] == L, 0, z["labels"])))
        edit_json(m / "discovery/hypotheses.json", lambda d: d.update(hypotheses=[h for h in d["hypotheses"] if h["label"] != L], count=d["count"] - 1))
        edit_json(m / "discovery/seeds.json", lambda d: d.update(seeds=[x for x in d["seeds"] if x["id"] != s[-1]["id"]]))
        refreeze(m, ["hypothesis-raster.npz", "hypotheses.json", "seeds.json"])

    def merge(m, v, c):
        if len(c.hyps) < 2:
            return {"not_applicable": "fewer than two hypotheses"}
        L1, L2 = c.hyps[0]["label"], c.hyps[1]["label"]
        edit_npz(m / "discovery/hypothesis-raster.npz", lambda z: z.__setitem__("labels", np.where(z["labels"] == L2, L1, z["labels"])))
        edit_json(m / "discovery/hypotheses.json", lambda d: d.update(hypotheses=[h for h in d["hypotheses"] if h["label"] != L2]))
        edit_json(m / "discovery/seeds.json", lambda d: d.update(seeds=[x for x in d["seeds"] if x["id"] != c.hyps[1]["id"]]))
        refreeze(m, ["hypothesis-raster.npz", "hypotheses.json", "seeds.json"])

    def _move_seed(m, hid, row, col):
        for name in ("discovery/seeds.json", "discovery/hypotheses.json"):
            def fn(d):
                if "seeds" in d:
                    for x in d["seeds"]:
                        if x["id"] == hid:
                            x["row"], x["col"] = row, col
                else:
                    for h in d["hypotheses"]:
                        if h["id"] == hid:
                            h["seed"]["row"], h["seed"]["col"] = row, col
            edit_json(m / name, fn)
        refreeze(m, ["seeds.json", "hypotheses.json"])

    def seed_off(m, v, c):
        lab = c.raster["labels"]
        h = c.hyps[0]
        rr, cc = np.nonzero((lab != h["label"]) & (lab > 0))
        k = int(np.argmin((rr - h["seed"]["row"]) ** 2 + (cc - h["seed"]["col"]) ** 2))
        _move_seed(m, h["id"], int(rr[k]), int(cc[k]))

    def seed_not_max(m, v, c):
        h = next((x for x in c.hyps if x["cells"] > 1 and x["seed"]["fallback"] is None and x["seed"]["clearance_rad"] > 0), None)
        if h is None:
            return {"not_applicable": "no multi-cell hypothesis with positive clearance"}
        lab, bnd = c.raster["labels"], c.raster["boundary"]
        rr, cc = np.nonzero((lab == h["label"]) & bnd)
        _move_seed(m, h["id"], int(rr[0]), int(cc[0]))

    def tie_break(m, v, c):
        h = next((x for x in c.hyps if (x["seed"]["tied_candidates"] or 0) > 1), None)
        if h is None:
            return {"not_applicable": "no tied seed"}
        lab, clr = c.raster["labels"].reshape(-1), c.raster["clearance_rad"].reshape(-1)
        member = np.flatnonzero(lab == h["label"])
        tied = sorted(member[np.nanmax(clr[member]) - clr[member] <= TIE_EPS].tolist())
        r_, c_ = divmod(tied[-1], W)
        _move_seed(m, h["id"], r_, c_)
        return {"note": f"{h['id']}: {divmod(tied[0], W)} -> {(r_, c_)}"}

    def add_oid(m, v, c):
        edit_npz(m / "input/range-sensory.npz", lambda z: z.__setitem__("object_index", c.exr()["oid"].astype(np.int32)))

    def open_rgb(m, v, c):
        edit_json(m / "discovery/discovery-opened-files.json", lambda d: d["events"].append(
            {"event": "open", "path": str((m / "input/rgb-sensory.npz").resolve()), "kind": "data-read", "allowed": True}))

    def open_catalog(m, v, c):
        edit_json(m / "discovery/discovery-opened-files.json", lambda d: d["events"].append(
            {"event": "open", "path": str(CATALOG), "kind": "data-read", "allowed": True}))

    def after_freeze(m, v, c):
        p = m / "discovery/hypotheses.csv"
        p.write_text(p.read_text() + "\n")

    def eval_first(m, v, c):
        def fn(d):
            o = [x for x in d["ordered_data_events"] if x != "freeze_verified"]
            o.append("freeze_verified"); d["ordered_data_events"] = o
        edit_json(m / "evaluation/evaluation-opened-files.json", fn)

    def overlap_value(m, v, c):
        edit_npz(m / "evaluation/overlap-matrix.npz", lambda z: z["cells"].__setitem__(0, z["cells"][0] + 1))

    def omit_o0(m, v, c):
        def fn(z):
            k = z["o"] != 0
            for n in ("h", "o", "cells", "support_sr"):
                z[n] = z[n][k]
        edit_npz(m / "evaluation/overlap-matrix.npz", fn)

    def rgb_modifies(m, v, c):
        lab0 = c.hyps[0]["label"]
        def fn(z):
            lab = z["labels"].copy(); cells = np.flatnonzero(lab.reshape(-1) == lab0)
            lab.reshape(-1)[cells[: max(1, len(cells) // 2)]] = lab.max() + 1
            z["labels"] = lab
        edit_npz(m / "discovery/hypothesis-raster.npz", fn)

    def pixel(m, v, c):
        from PIL import Image
        p = v / "overview.png"
        img = Image.open(p.resolve()).convert("RGB"); img.putpixel((3, 3), (255, 0, 0)); p.unlink(); img.save(p)

    def fov3d(m, v, c):
        return {"fov3d_changed": True}

    def controller_code(m, v, c):
        return {"changed_files": changed_files(c) + ["tools/controller/check_controller02.py"]}

    def blender_proc(m, v, c):
        with open(m / "process-log.jsonl", "a") as f:
            f.write(json.dumps({"command": "discover", "argv": ["blender", "-b", "x.blend"], "status": "ok"}) + "\n")

    def controller_proc(m, v, c):
        with open(m / "process-log.jsonl", "a") as f:
            f.write(json.dumps({"command": "controller02", "argv": ["fov3d/experiments/classroom_oracle/controller02.py"],
                                "status": "ok"}) + "\n")

    def alter_c(m, v, c):
        edit_npz(m / "discovery/continuity-edges.npz", lambda z: z["C"].__setitem__(1, z["C"][1] * 1.01))
        refreeze(m, ["continuity-edges.npz"])

    def alter_range(m, v, c):
        def fn(z):
            r = z["range_m"].copy(); k = np.argwhere(z["valid_mask"])[0]; r[tuple(k)] += 0.1; z["range_m"] = r
        edit_npz(m / "input/range-sensory.npz", fn)

    def alter_clearance(m, v, c):
        def fn(z):
            cl = z["clearance_rad"].copy(); k = np.argwhere(np.isfinite(cl) & (cl > 0))
            if len(k):
                cl[tuple(k[0])] += 1e-6
            z["clearance_rad"] = cl
        edit_npz(m / "discovery/hypothesis-raster.npz", fn); refreeze(m, ["hypothesis-raster.npz"])

    def flip_boundary(m, v, c):
        def fn(z):
            b = z["boundary"].copy(); k = np.argwhere(z["labels"] > 0)[0]; b[tuple(k)] = ~b[tuple(k)]; z["boundary"] = b
        edit_npz(m / "discovery/hypothesis-raster.npz", fn); refreeze(m, ["hypothesis-raster.npz"])

    def swap_ids(m, v, c):
        if len(c.hyps) < 2:
            return {"not_applicable": "fewer than two hypotheses"}
        a_, b_ = c.hyps[0]["label"], c.hyps[1]["label"]
        edit_npz(m / "discovery/hypothesis-raster.npz", lambda z: z.__setitem__(
            "labels", np.where(z["labels"] == a_, b_, np.where(z["labels"] == b_, a_, z["labels"]))))
        refreeze(m, ["hypothesis-raster.npz"])

    def synth(m, v, c):
        edit_json(m / "synthetic/synthetic-report.json", lambda d: d["cases"][0].update(ok=False))

    return [
        ("MAX_SURFACE_SLANT_DEG changed to 70", "13", slant),
        ("one retained edge flipped", "14", flip_edge),
        ("longitude wrapping broken (regenerated without wrap)", "10", lambda m, v, c: regenerate(m, wrap=False)),
        ("constant pixel spacing instead of true delta (regenerated)", "11", lambda m, v, c: regenerate(m, true_delta=False)),
        ("one hypothesis label altered", "15", label),
        ("a singleton component deleted", "16", del_singleton),
        ("two components merged", "18", merge),
        ("seed moved off its hypothesis", "22", seed_off),
        ("seed moved away from the maximum-clearance cell", "22", seed_not_max),
        ("seed tie-break violated", "23", tie_break),
        ("Object Index added to the sensory input", "05", add_oid),
        ("discovery opened RGB", "07", open_rgb),
        ("discovery opened the catalog", "08", open_catalog),
        ("a bootstrap output modified after the freeze", "24", after_freeze),
        ("evaluation before a valid freeze", "24", eval_first),
        ("one overlap value altered", "26", overlap_value),
        ("O_0 omitted from the overlap", "27", omit_o0),
        ("RGB step modified a hypothesis", "28", rgb_modifies),
        ("a visual pixel altered", "29", pixel),
        ("fov3d modified", "30", fov3d),
        ("controller code modified", "30", controller_code),
        ("Blender command in the process log", "02", blender_proc),
        ("controller command in the process log", "32", controller_proc),
        ("one C value altered", "12", alter_c),
        ("one range value altered", "04", alter_range),
        ("one clearance value altered", "21", alter_clearance),
        ("one boundary cell flipped", "20", flip_boundary),
        ("hypothesis ids swapped", "19", swap_ids),
        ("synthetic known-answer case failed", "33", synth),
    ]


def corruption_suite(run: Path, vis: Path) -> tuple[int, int, list]:
    caught = total = 0
    results = []
    for name, target, fn in corruptions():
        with tempfile.TemporaryDirectory(prefix="nb1a-corrupt-") as td:
            m, v = mirror(run, vis, Path(td))
            with contextlib.redirect_stdout(io.StringIO()):
                overrides = fn(m, v, Ctx(m, v)) or {}
            if "not_applicable" in overrides:
                print(f"{PREFIX} corruption N/A [{target}] {name}: {overrides['not_applicable']}")
                results.append({"name": name, "target": target, "not_applicable": overrides["not_applicable"]})
                continue
            total += 1
            note = overrides.pop("note", "")
            ctx = Ctx(m, v)
            for k, val in overrides.items():
                setattr(ctx, k, val)
            with contextlib.redirect_stdout(io.StringIO()):
                res = run_checks(ctx, quiet=True)
            failed = sorted(r["check"] for r in res if not r["ok"])
            hit = target in failed
            caught += hit
            results.append({"name": name, "target": target, "caught": hit, "failed": failed, "note": note})
            print(f"{PREFIX} corruption {'CAUGHT' if hit else 'MISSED'} [{target}] {name}"
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
        print(f"{PREFIX} NATURAL_BOOTSTRAP1A_CHECKS_PASS")
    out = {"schema": "NB1a-check-summary-v1", "checks": res, "passed": ok, "code": git("rev-parse", "HEAD").strip()}
    if a.corruptions:
        caught, total, results = corruption_suite(run, vis)
        out["corruptions"] = {"caught": caught, "total": total, "baseline_passing": ok, "results": results}
        print(f"{PREFIX} CORRUPTIONS caught={caught}/{total}" + ("" if ok else " (NOT PROBATIVE: baseline failing)"))
        if ok and caught == total:
            print(f"{PREFIX} NATURAL_BOOTSTRAP1A_MUTATIONS_CAUGHT")
        ok = ok and caught == total
    if a.write_summary:
        (run / "check-summary.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
