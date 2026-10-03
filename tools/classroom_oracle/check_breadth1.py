"""Breadth-1: fail-capable checks of the Classroom-234 spherical glance.

    .venv/bin/python tools/classroom_oracle/check_breadth1.py --run RUN --visuals VIS [--corruptions] [--write-summary]

Contract: docs/classroom-oracle/breadth-1-spherical-glance-contract.md, section 8 (checks 1-26).  The
checker recomputes from the canonical EXR, which it reads with the independent ``OpenEXR`` package, and
from the accepted sources.  It keeps its own literal copy of the frozen configuration and of the accepted
hashes.  It computes the cell weights with an independent formula (2 dlambda cos(phi_c) sin(dphi/2)) and
the components with its own seam-aware breadth-first search.  ``--corruptions`` plants defects in
throwaway mirrors (JSON copied, other files linked) or in-process mutants; every defect must make its
targeted check fail.  The canonical outputs are never modified; ``--write-summary`` writes only
``check-summary.json``.
"""
from __future__ import annotations

import argparse
import ast
import collections
import contextlib
import copy
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
PREFIX = "[breadth1-check]"

# ---- literal copies (contract sections 2-3); deliberately not imported from breadth1_spec
W, H = 720, 360
CFG = {"camera_type": "PANO", "panorama_type": "EQUIRECTANGULAR", "samples": 512, "seed": 0,
       "adaptive_sampling": False, "denoising": False, "motion_blur": False, "pixel_filter": "BOX",
       "filter_width": 1.0, "device_backend": "OPTIX", "engine": "CYCLES", "resolution_percentage": 100,
       "film_transparent": False, "exr_codec": "NONE", "file_format": "OPEN_EXR_MULTILAYER"}
LON, LAT = (-math.pi, math.pi), (-math.pi / 2, math.pi / 2)
SHARED = Path("/home/lvelho/rd/f3d-vision")
BASE = "3aa0cc6777401ddef1eb6755bff60515d87bd2db"
ACCEPTED = {
    "previews/controller-01-full/bootstrap/seeds.json": "6ef833196de2462370ba4b2a2a8eed3fbde7f0a61e5aa6cbaf95f66947134c4f",
    "previews/controller-01-full/bootstrap/instance_catalog.json": "be26594254b03fbda7216ac1a942a5c800cf4bdd8f79751a2b8c22d6bfb4c7ae",
    "previews/controller-02-classroom-replay/result.json": "a6dc4879f70216f99d098841f9d2c33dda0ceb71f01a4ab76320b0d08212dc55",
    "previews/controller-01-full/manifest.json": "d293a98fd6bb285e882186af8fbeadba29ab1d1d62efea23f3ed0ff5c62c0e91",
    "previews/controller-01-full/actions.json": "12cdbe4d760cce6c494075e4368f9424805b51b997b8b21724bf87f71cc55afd",
    "previews/controller-02-classroom-replay/manifest.json": "ad49e835c2efbbead7732b97dc140733bb5d947ef1808ff86325e85c5da4014f",
    "previews/controller-02-classroom-replay/actions.json": "7fb86aba9bfdc6da0a67828be233b72893cec31b6c02609c5b883b1a1b66f047",
}
SEEDS, CATALOG, C02 = list(ACCEPTED)[:3]
CATALOG_COUNT = 234
DOMAIN = ((-25.0, 25.0), (-20.0, 20.0))
BREADTH1_FILES = {"docs/classroom-oracle/breadth-1-spherical-glance-contract.md",
                  "docs/classroom-oracle/breadth-1-spherical-glance-report.md",
                  "tools/repository/check_repository_layout.py"} | {
    f"tools/classroom_oracle/{n}" for n in ("breadth1_spec.py", "breadth1_render.py", "breadth1_glance.py",
                                            "breadth1_visuals.py", "check_breadth1.py")}
TOOLS = sorted(f for f in BREADTH1_FILES if f.endswith(".py") and "breadth1" in f)
FORBIDDEN_IMPORTS = re.compile(r"^(fov3d\.control|fov3d\.experiments\.classroom_oracle\.controller|classroom_oracle1_run|"
                               r"classroom_oracle1_matcher|classroom_oracle1_epistemic|classroom_oracle1_eval|"
                               r"multiobject2c_policy|fsg6f_frontier|fsg6f_public|fsg3_surface_map|fsg_stereo|"
                               r"controller0)")
TRUTHS = {"REFERENCE / EVALUATION", "ORACLE INPUT", "DERIVED"}
OUTPUTS = ["glance.npz", "range.npz", "components.npz", "object-stats.json", "object-stats.csv", "components.json",
           "seed-directions.json", "summary.json", "global-point-cloud.ply"]
FIGURES = ["overview.png", "rgb-panorama.png", "range-panorama.png", "instance-panorama.png",
           "object-boundary-overlay.png", "seed-direction-panorama.png", "support-size-histogram.png",
           "support-vs-range.png"]
REQUIRED_BADGES = {"rgb-panorama.png": "REFERENCE / EVALUATION", "range-panorama.png": "REFERENCE / EVALUATION",
                   "instance-panorama.png": "ORACLE INPUT", "seed-direction-panorama.png": "DERIVED",
                   "support-size-histogram.png": "DERIVED", "support-vs-range.png": "DERIVED"}
RTOL = 1e-12
# contract section 11 (post-run numerical clarification): literal copies, not imported from the generator
SEED_TIE_DOT_EPS = 1e-12
SEED_TIE_CONTROLS = [([(60, 28), (60, 29)], (60, 28)),
                     ([(179, 359), (179, 360), (180, 359), (180, 360)], (179, 359)),
                     ([(179, 719), (179, 0), (180, 719), (180, 0)], (179, 0))]
_CACHE: dict = {}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def rel_close(a: float, b: float, rtol: float = RTOL, atol: float = 1e-18) -> bool:
    return abs(a - b) <= atol + rtol * max(abs(a), abs(b))


# ------------------------------------------------------------------ independent geometry
def weights_independent() -> np.ndarray:
    dlam, dphi = 2 * math.pi / W, math.pi / H
    phi_c = math.pi / 2 - (np.arange(H) + 0.5) * dphi
    return 2.0 * dlam * np.cos(phi_c) * math.sin(dphi / 2)


def centres() -> tuple[np.ndarray, np.ndarray]:
    return -180.0 + 0.5 * (np.arange(W) + 0.5), 90.0 - 0.5 * (np.arange(H) + 0.5)


def unit(yaw_deg, pitch_deg) -> np.ndarray:
    y, p = np.radians(yaw_deg), np.radians(pitch_deg)
    return np.stack([np.sin(y) * np.cos(p), np.sin(p), -np.cos(y) * np.cos(p)], -1)


def bfs_components(mask: np.ndarray, wrap: bool = True) -> list[list[tuple[int, int]]]:
    """Seam-aware 8-connected components by breadth-first search (independent of the generator)."""
    seen = np.zeros(mask.shape, bool)
    comps = []
    for r0, c0 in zip(*np.nonzero(mask)):
        if seen[r0, c0]:
            continue
        q = collections.deque([(int(r0), int(c0))])
        seen[r0, c0] = True
        cells = []
        while q:
            r, c = q.popleft()
            cells.append((r, c))
            for dr in (-1, 0, 1):
                rr = r + dr
                if rr < 0 or rr >= H:
                    continue
                for dc in (-1, 0, 1):
                    cc = (c + dc) % W
                    if not wrap and not 0 <= c + dc < W:
                        continue
                    if (dr or dc) and mask[rr, cc] and not seen[rr, cc]:
                        seen[rr, cc] = True
                        q.append((rr, cc))
        comps.append(cells)
    return comps


def seed_of(comps: list[dict], dirs: np.ndarray, wts: np.ndarray) -> tuple[tuple[int, int], bool, int | None]:
    """Contract 4.5 + section 11, independently: largest component, weighted mean, ties within the epsilon."""
    big = comps[0]
    dd = dirs[big["rows"], big["cols"]]
    m = (dd * wts[big["rows"]][:, None]).sum(0)
    nm = float(np.linalg.norm(m))
    if nm < 1e-9:
        return tuple(big["min_rc"]), True, None
    dots = dd @ (m / nm)
    tied = np.flatnonzero(dots.max() - dots <= SEED_TIE_DOT_EPS)
    return min((int(big["rows"][k]), int(big["cols"][k])) for k in tied), False, int(len(tied))


def ordered_bfs(mask: np.ndarray, wts: np.ndarray) -> list[dict]:
    comps = []
    for cells in bfs_components(mask):
        rr = np.array([c[0] for c in cells]); cc = np.array([c[1] for c in cells])
        comps.append({"rows": rr, "cols": cc, "cells": len(cells),
                      "omega": float(np.bincount(rr, minlength=H) @ wts), "min_rc": list(min(cells))})
    comps.sort(key=lambda c: (-c["omega"], -c["cells"], c["min_rc"][0], c["min_rc"][1]))
    return comps


def tie_controls() -> list[tuple[tuple[int, int], tuple[int, int], int | None, int]]:
    """Known-answer controls on exactly mirror-symmetric synthetic components: (want, got, tied, n)."""
    wts = weights_independent()
    yc, pc = centres()
    dirs = unit(*np.meshgrid(yc, pc))
    out = []
    for cells, want in SEED_TIE_CONTROLS:
        mask = np.zeros((H, W), bool)
        for r, c in cells:
            mask[r, c] = True
        comps = ordered_bfs(mask, wts)
        got, _fb, tied = seed_of(comps, dirs, wts)
        out.append((want, got, tied, len(comps)))
    return out


# ------------------------------------------------------------------ context
class Ctx:
    def __init__(self, run: Path, vis: Path):
        self.run, self.vis = Path(run), Path(vis)
        j = lambda p: json.loads((self.run / p).read_text())  # noqa: E731
        self.meta = j("render/render-metadata.json")
        self.manifest = j("manifest.json")
        self.stats = j("object-stats.json")
        self.components = j("components.json")
        self.seeds = j("seed-directions.json")
        self.summary = j("summary.json")
        self.preflight = j("preflight.json")
        self.synthetic = j("synthetic/synthetic-report.json")
        self.processes = [json.loads(l) for l in (self.run / "process-log.jsonl").read_text().splitlines() if l.strip()]
        self.vmanifest = json.loads((self.vis / "visuals-manifest.json").read_text())
        self.source_files = {k: SHARED / k for k in ACCEPTED}
        self.seeds_src = json.loads(self.source_files[SEEDS].read_text())
        self.catalog = {int(e["instance_id"]): e["object_name"]
                        for e in json.loads(self.source_files[CATALOG].read_text())["instances"]}
        self.c02 = json.loads(self.source_files[C02].read_text())
        self.r_wh = np.asarray(self.seeds_src["head_R_wh"], np.float64)
        self.o_w = np.asarray(self.seeds_src["head_origin_w_m"], np.float64)
        exr = self.run / "render/canonical.exr"
        key = ("exr", sha256(exr))
        if key not in _CACHE:
            import OpenEXR
            with OpenEXR.File(str(exr), separate_channels=True) as f:
                window = tuple(np.array(v).tolist() for v in f.header()["dataWindow"])  # read before close
                ch = {k: np.array(v.pixels) for k, v in f.channels().items()}
            _CACHE[key] = (window, ch)
        self.data_window, ch = _CACHE[key]
        pick = lambda s: next(v for k, v in ch.items() if k.endswith(s))  # noqa: E731
        self.raw_index = pick("Object Index.X").astype(np.float64)
        self.instance = np.rint(self.raw_index).astype(np.int64)
        self.position = np.stack([pick(f"Position.{c}") for c in "XYZ"], -1).astype(np.float32)
        self.rgb = np.stack([pick(f"Combined.{c}") for c in "RGB"], -1).astype(np.float32)
        self.glance = np.load(self.run / "glance.npz")
        self.range_npz = np.load(self.run / "range.npz")
        self.comp_raster = np.load(self.run / "components.npz")["component_ordinal"]
        self.changed_files = None
        self.fov3d_changed = None

    # derived recomputations (cached on the raster content)
    def recompute(self) -> dict:
        key = ("rec", hashlib.sha256(self.instance.tobytes() + self.position.tobytes()).hexdigest())
        if key in _CACHE:
            return _CACHE[key]
        inst, pos = self.instance, self.position
        wts = weights_independent()
        yc, pc = centres()
        dirs = unit(*np.meshgrid(yc, pc))
        zero = np.all(pos == 0, axis=-1)
        cls = np.where(inst != 0, 1, np.where(zero, 3, 2)).astype(np.int8)
        d = pos.astype(np.float64) - self.o_w
        rng = np.sqrt((d * d).sum(-1))
        rng[cls == 3] = np.nan
        in_dom = ((yc[None, :] >= DOMAIN[0][0]) & (yc[None, :] <= DOMAIN[0][1])
                  & (pc[:, None] >= DOMAIN[1][0]) & (pc[:, None] <= DOMAIN[1][1]))
        objs = {}
        for oid in sorted(self.catalog):
            mask = inst == oid
            n = int(mask.sum())
            if not n:
                objs[oid] = {"cells": 0}
                continue
            omega = float((mask.sum(axis=1) * wts).sum())
            comps = ordered_bfs(mask, wts)
            seed, fb, tied = seed_of(comps, dirs, wts)
            r = rng[mask]
            objs[oid] = {"cells": n, "omega": omega, "comps": comps, "seed": seed, "fallback": fb, "tied": tied,
                         "range": (float(np.min(r)), float(np.median(r)), float(np.max(r))),
                         "intersects": bool((mask & in_dom).any()), "outside": int((mask & ~in_dom).sum())}
        out = {"weights": wts, "cls": cls, "range": rng, "objs": objs, "yc": yc, "pc": pc}
        _CACHE[key] = out
        return out

    def objects(self) -> dict:
        return {o["instance_id"]: o for o in self.stats["objects"]}


def git(*args) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout


def changed_files(ctx: Ctx) -> list[str]:
    if ctx.changed_files is not None:
        return ctx.changed_files
    ch = set(git("diff", "--name-only", BASE).split()) | set(git("diff", "--name-only", "--cached", BASE).split())
    ch |= {p for p in git("ls-files", "--others", "--exclude-standard").split() if p.startswith(("tools/", "docs/", "fov3d/"))}
    return sorted(ch)


def fov3d_changed(ctx: Ctx) -> bool:
    if ctx.fov3d_changed is not None:
        return ctx.fov3d_changed
    diff = subprocess.run(["git", "diff", "--quiet", BASE, "--", "fov3d"], cwd=REPO).returncode != 0
    untracked = bool(git("ls-files", "--others", "--exclude-standard", "--", "fov3d").strip())
    return diff or untracked


# ------------------------------------------------------------------ checks
def c01(ctx):
    dw = ctx.data_window
    lo, hi = [list(map(int, v)) for v in dw]
    cfg = ctx.meta["config"]
    ok = (lo == [0, 0] and hi == [W - 1, H - 1] and ctx.instance.shape == (H, W)
          and cfg["resolution_wh"] == [W, H] and cfg["resolution_percentage"] == 100
          and ctx.glance["instance"].shape == (H, W))
    return ok, f"dataWindow {lo}-{hi}, metadata {cfg['resolution_wh']}"


def c02(ctx):
    bad = []
    for which in ("config", "config_after_render"):
        cfg = ctx.meta.get(which) or {}
        for k, v in CFG.items():
            if cfg.get(k) != v:
                bad.append(f"{which}.{k}={cfg.get(k)!r}")
        if not (np.allclose(cfg.get("longitude_rad", [0, 0]), LON, atol=1e-6)
                and np.allclose(cfg.get("latitude_rad", [0, 0]), LAT, atol=1e-6)):
            bad.append(f"{which} longitude/latitude {cfg.get('longitude_rad')} {cfg.get('latitude_rad')}")
        if cfg.get("passes") != {"combined": True, "position": True, "object_index": True}:
            bad.append(f"{which}.passes")
    rec = ctx.recompute()
    mask = rec["cls"] == 1
    p = (ctx.position.astype(np.float64) - ctx.o_w) @ ctx.r_wh
    yaw = np.degrees(np.arctan2(p[..., 0], -p[..., 2]))
    pitch = np.degrees(np.arctan2(p[..., 1], np.hypot(p[..., 0], p[..., 2])))
    dyaw = (yaw - rec["yc"][None, :] + 180.0) % 360.0 - 180.0
    dpitch = pitch - rec["pc"][:, None]
    tol = 1e-3
    out = mask & ((np.abs(dpitch) > 0.25 + tol) | (np.abs(dyaw) > 0.25 + tol / np.maximum(np.cos(np.radians(pitch)), 1e-12)))
    if out.any() or not mask.any():
        bad.append(f"orientation: {int(out.sum())} of {int(mask.sum())} authored cells outside their declared cell")
    return not bad, "; ".join(bad[:4]) or f"PANO/EQUIRECTANGULAR full sphere; {int(mask.sum())} authored cells inside their cells"


def c03(ctx):
    m = ctx.meta
    cam = np.asarray(m["config"]["camera_matrix_world"], np.float64)
    req_ok = (m["head_R_wh_requested"] == ctx.seeds_src["head_R_wh"]
              and m["head_origin_w_m_requested"] == ctx.seeds_src["head_origin_w_m"])
    dr = float(np.max(np.abs(cam[:3, :3] - ctx.r_wh)))
    do = float(np.max(np.abs(cam[:3, 3] - ctx.o_w)))
    eye = m["eye_check"]
    man = (ctx.manifest["head_R_wh"] == ctx.seeds_src["head_R_wh"]
           and ctx.manifest["head_origin_w_m"] == ctx.seeds_src["head_origin_w_m"])
    ok = (req_ok and dr <= 1e-6 and do <= 1e-6 and eye["max_abs_rotation_diff"] <= 1e-6
          and eye["max_abs_origin_diff"] <= 1e-6 and man and m["seeds_sha256"] == ACCEPTED[SEEDS]
          and sha256(ctx.source_files[SEEDS]) == ACCEPTED[SEEDS])
    return ok, f"requested exact {req_ok}; Blender matrix diff {dr:.2g}/{do:.2g}; EYE {eye['max_abs_rotation_diff']:.2g}"


def c04(ctx):
    names = {int(k): v for k, v in ctx.meta["instance_names"].items()}
    ok = (sha256(ctx.source_files[CATALOG]) == ACCEPTED[CATALOG] and len(ctx.catalog) == CATALOG_COUNT
          and names == ctx.catalog and ctx.meta["catalog_sha256"] == ACCEPTED[CATALOG]
          and ctx.meta["catalog_check"]["equal"] is True and ctx.meta["catalog_check"]["live_count"] == CATALOG_COUNT)
    return ok, f"catalog {len(ctx.catalog)}, live {len(names)}"


def c05(ctx):
    ids = set(np.unique(ctx.instance).tolist()) - {0}
    illegal = sorted(ids - set(ctx.catalog))
    integral = bool(np.all(ctx.raw_index == np.rint(ctx.raw_index)) and ctx.raw_index.min() >= 0)
    return not illegal and integral, f"{len(ids)} rendered ids; illegal {illegal[:5]}; integral {integral}"


def c06(ctx):
    objs = ctx.stats["objects"]
    ids = [o["instance_id"] for o in objs]
    names_ok = all(ctx.catalog.get(o["instance_id"]) == o["object_name"] for o in objs)
    rows = list(__import__("csv").DictReader(io.StringIO((ctx.run / "object-stats.csv").read_text())))
    csv_ok = sorted(int(r["instance_id"]) for r in rows) == sorted(ctx.catalog) and len(rows) == CATALOG_COUNT
    ok = (len(objs) == CATALOG_COUNT and len(set(ids)) == len(ids) and set(ids) == set(ctx.catalog) and names_ok
          and ctx.stats["count"] == CATALOG_COUNT and csv_ok)
    return ok, f"{len(objs)} records, {len(set(ids))} unique, names {names_ok}, csv {csv_ok}"


def c07(ctx):
    rec = ctx.recompute()["objs"]
    s = ctx.summary
    bad = [o["instance_id"] for o in ctx.stats["objects"]
           if o["status"] != ("VISIBLE_AT_0P5_DEG" if rec[o["instance_id"]]["cells"] else "NO_FIRST_HIT_AT_0P5_DEG")]
    nv = sum(1 for v in rec.values() if v["cells"])
    ok = (not bad and s["visible_at_0p5_deg"] + s["no_first_hit_at_0p5_deg"] == CATALOG_COUNT == s["catalog_total"]
          and s["visible_at_0p5_deg"] == nv)
    return ok, f"visible {s['visible_at_0p5_deg']} + no first hit {s['no_first_hit_at_0p5_deg']} = {s['catalog_total']}; wrong {bad[:5]}"


def c08(ctx):
    wi = weights_independent()
    ws = ctx.range_npz["cell_weights_sr"]
    tot = float(wi.sum() * W)
    ok = (ws.shape == (H,) and np.allclose(ws, wi, rtol=1e-12, atol=0) and abs(tot - 4 * math.pi) < 1e-12
          and abs(float(ws.sum() * W) - 4 * math.pi) < 1e-12 and abs(ctx.summary["sphere_solid_angle_sr"] - 4 * math.pi) < 1e-12)
    return ok, f"sum {tot!r} vs 4pi {4 * math.pi!r}; max rel diff {float(np.max(np.abs(ws / wi - 1))):.2g}"


def c09(ctx):
    rec = ctx.recompute()["objs"]
    bad = []
    for o in ctx.stats["objects"]:
        r = rec[o["instance_id"]]
        if o["visible_cells"] != r["cells"]:
            bad.append((o["instance_id"], "cells"))
        elif r["cells"] and not (rel_close(o["solid_angle_sr"], r["omega"])
                                 and rel_close(o["fraction_of_4pi"], r["omega"] / (4 * math.pi))):
            bad.append((o["instance_id"], "solid angle"))
        elif not r["cells"] and o["solid_angle_sr"] != 0:
            bad.append((o["instance_id"], "nonzero"))
    return not bad, f"{len(bad)} mismatches {bad[:5]}"


def c10(ctx):
    rec = ctx.recompute()["objs"]
    bad = []
    ccount = collections.Counter()
    for o in ctx.stats["objects"]:
        oid = o["instance_id"]
        r = rec[oid]
        if not r["cells"]:
            if o["components"] != 0 or str(oid) in ctx.components["objects"]:
                bad.append((oid, "invisible has components"))
            continue
        stored = ctx.components["objects"].get(str(oid), [])
        ccount[len(r["comps"])] += 1
        if o["components"] != len(r["comps"]) or len(stored) != len(r["comps"]):
            bad.append((oid, f"count {o['components']}/{len(stored)} vs {len(r['comps'])}"))
            continue
        for k, (s, c) in enumerate(zip(stored, r["comps"]), start=1):
            cells = ctx.comp_raster[c["rows"], c["cols"]]
            if (s["ordinal"] != k or s["cells"] != c["cells"] or s["min_rc"] != c["min_rc"]
                    or not rel_close(s["solid_angle_sr"], c["omega"]) or not np.all(cells == k)):
                bad.append((oid, f"component {k}"))
                break
        if o.get("largest_component_cells") != r["comps"][0]["cells"]:
            bad.append((oid, "largest"))
    if int((ctx.comp_raster > 0).sum()) != int((ctx.instance > 0).sum()):
        bad.append(("raster", "coverage"))
    s = ctx.summary
    if s["visible_with_multiple_components"] != sum(v for k, v in ccount.items() if k > 1):
        bad.append(("summary", "multi"))
    if s["component_count_distribution"] != {str(k): v for k, v in sorted(ccount.items())}:
        bad.append(("summary", "distribution"))
    return not bad, f"{len(bad)} mismatches {bad[:4]}"


def c11(ctx):
    rec = ctx.recompute()
    a, b = ctx.range_npz["range_m"], rec["range"]
    same_nan = np.array_equal(np.isnan(a), np.isnan(b))
    diff = float(np.nanmax(np.abs(a - b))) if same_nan and np.isfinite(a).any() else math.inf
    return same_nan and diff <= 1e-9, f"max |range diff| {diff:.2g} m; NaN pattern equal {same_nan}"


def c12(ctx):
    rec = ctx.recompute()["objs"]
    bad = []
    for o in ctx.stats["objects"]:
        r = rec[o["instance_id"]]
        if not r["cells"]:
            if o["range_m"] is not None:
                bad.append(o["instance_id"])
            continue
        got = (o["range_m"]["min"], o["range_m"]["median"], o["range_m"]["max"])
        if not all(abs(x - y) <= 1e-9 for x, y in zip(got, r["range"])):
            bad.append(o["instance_id"])
    return not bad, f"{len(bad)} mismatches {bad[:5]}"


def c13(ctx):
    rec = ctx.recompute()["objs"]
    yc, pc = centres()
    seeds = {s["instance_id"]: s for s in ctx.seeds["seeds"]}
    bad = []
    nvis = 0
    for o in ctx.stats["objects"]:
        oid = o["instance_id"]
        r = rec[oid]
        if not r["cells"]:
            if o["seed"] is not None or oid in seeds:
                bad.append((oid, "seed for invisible"))
            continue
        nvis += 1
        s, so = seeds.get(oid), o["seed"]
        if s is None or so is None:
            bad.append((oid, "missing"))
            continue
        rc = (s["row"], s["col"])
        big = r["comps"][0]
        on_big = any(int(rr) == rc[0] and int(cc) == rc[1] for rr, cc in zip(big["rows"], big["cols"]))
        if (ctx.instance[rc] != oid or not on_big or rc != r["seed"] or s["fallback"] != r["fallback"]
                or s.get("tied_candidates") != r["tied"] or so.get("tied_candidates") != r["tied"]
                or (so["row"], so["col"]) != rc or s["yaw_deg"] != float(yc[rc[1]]) or s["pitch_deg"] != float(pc[rc[0]])
                or so["yaw_deg"] != s["yaw_deg"] or so["pitch_deg"] != s["pitch_deg"]):
            bad.append((oid, f"seed {rc} vs {r['seed']}"))
    eps_ok = (ctx.seeds.get("tie_semantics", {}).get("SEED_TIE_DOT_EPS") == SEED_TIE_DOT_EPS
              and ctx.manifest.get("seed_tie_rule", {}).get("SEED_TIE_DOT_EPS") == SEED_TIE_DOT_EPS
              and all(c["ok"] for c in ctx.manifest["seed_tie_rule"]["control"]))
    controls = tie_controls()
    ctl_ok = all(got == want and comps == 1 and tied == len(cells)
                 for (want, got, tied, comps), (cells, _w) in zip(controls, SEED_TIE_CONTROLS))
    ties = sum(1 for v in rec.values() if v["cells"] and (v["tied"] or 0) > 1)
    ok = not bad and len(seeds) == nvis and eps_ok and ctl_ok
    return ok, (f"{nvis} seeds ({ties} with numerically tied candidates); {len(bad)} wrong {bad[:3]}; "
                f"declared epsilon {eps_ok}; independent tie controls {ctl_ok} {[c[:2] for c in controls]}")


def c14(ctx):
    rec = ctx.recompute()["objs"]
    bad = [o["instance_id"] for o in ctx.stats["objects"] if rec[o["instance_id"]]["cells"] and (
        o["intersects_old_controller_domain"] != rec[o["instance_id"]]["intersects"]
        or o["outside_old_controller_domain_cells"] != rec[o["instance_id"]]["outside"])]
    bad += [o["instance_id"] for o in ctx.stats["objects"] if not rec[o["instance_id"]]["cells"]
            and o["intersects_old_controller_domain"]]
    vis = [v for v in rec.values() if v["cells"]]
    d = ctx.summary["old_controller_domain"]
    ok = (not bad and d["visible_intersecting"] == sum(v["intersects"] for v in vis)
          and d["visible_entirely_outside"] == sum(not v["intersects"] for v in vis)
          and d["visible_with_any_support_outside"] == sum(v["outside"] > 0 for v in vis)
          and d["yaw_deg"] == list(DOMAIN[0]) and d["pitch_deg"] == list(DOMAIN[1]))
    return ok, f"{len(bad)} wrong flags {bad[:5]}"


def c15(ctx):
    a = sorted(int(k) for k in ctx.c02["final_states"])
    b = sorted(int(s["instance_id"]) for s in ctx.seeds_src["instances"])
    acc_seed = {int(s["instance_id"]): s["seed_gaze_deg"] for s in ctx.seeds_src["instances"]}
    srcs = sha256(ctx.source_files[C02]) == ACCEPTED[C02] and a == b and len(a) == 25
    bad = [o["instance_id"] for o in ctx.stats["objects"] if o["in_accepted_localized_25"] != (o["instance_id"] in a)]
    for o in ctx.stats["objects"]:
        if o["seed"] is None:
            continue
        exp = None
        if o["instance_id"] in acc_seed:
            u, v = unit(o["seed"]["yaw_deg"], o["seed"]["pitch_deg"]), unit(*acc_seed[o["instance_id"]])
            exp = math.degrees(math.acos(max(-1.0, min(1.0, float(u @ v)))))
        got = o["seed_separation_from_accepted_deg"]
        if (exp is None) != (got is None) or (exp is not None and abs(exp - got) > 1e-6):
            bad.append(o["instance_id"])
    acc = ctx.summary["accepted_localized_25"]
    vis_acc = [o["instance_id"] for o in ctx.stats["objects"] if o["instance_id"] in a and o["visible_cells"]]
    ok = (srcs and not bad and acc["total"] == 25 and acc["visible"] == len(vis_acc)
          and acc["no_first_hit"] == sorted(set(a) - set(vis_acc))
          and acc["visible_outside_accepted_25"] == ctx.summary["visible_at_0p5_deg"] - len(vis_acc))
    return ok, f"sources agree {srcs}; {len(bad)} wrong flags {bad[:5]}"


def c16(ctx):
    rec = ctx.recompute()["objs"]
    vis = sorted([oid for oid, v in rec.items() if v["cells"]], key=lambda i: (-rec[i]["omega"], -rec[i]["cells"], i))
    want = {oid: k for k, oid in enumerate(vis, start=1)}
    bad = [o["instance_id"] for o in ctx.stats["objects"] if o["rank"] != want.get(o["instance_id"])]
    rank_list = [r["instance_id"] for r in ctx.summary["ranking"]]
    om = [rec[i]["omega"] for i in vis]
    tk_ok = all(rel_close(ctx.summary["top_k_cumulative_support"][str(k)]["solid_angle_sr"], float(sum(om[:k])), 1e-10)
                for k in (1, 5, 10, 25))
    ok = not bad and rank_list == vis and tk_ok
    return ok, f"{len(bad)} wrong ranks {bad[:5]}; ranking list {rank_list == vis}; top-K {tk_ok}"


def c17(ctx):
    data = (ctx.run / "global-point-cloud.ply").read_bytes()
    end = data.index(b"end_header\n") + len(b"end_header\n")
    head = data[:end].decode("ascii")
    n = int(re.search(r"element vertex (\d+)", head).group(1))
    dt = np.dtype([("x", "<f4"), ("y", "<f4"), ("z", "<f4"), ("r", "u1"), ("g", "u1"), ("b", "u1"),
                   ("i", "<i4"), ("row", "<u2"), ("col", "<u2")])
    body = data[end:]
    rows, cols = np.nonzero(ctx.instance > 0)
    ok = len(body) == n * dt.itemsize and n == len(rows)
    detail = f"PLY {n} vertices, authored cells {len(rows)}"
    if ok:
        v = np.frombuffer(body, dt)
        g = np.rint(np.power(np.clip(ctx.rgb[rows, cols].astype(np.float64), 0, 1), 1 / 2.2) * 255).astype(np.uint8)
        ok = (np.array_equal(v["row"], rows) and np.array_equal(v["col"], cols)
              and np.array_equal(v["i"], ctx.instance[rows, cols])
              and np.array_equal(np.stack([v["x"], v["y"], v["z"]], -1), ctx.position[rows, cols])
              and np.array_equal(np.stack([v["r"], v["g"], v["b"]], -1), g))
        detail += f"; per-vertex position/rgb/id/cell equal {ok}"
    vis_ply = ctx.vis / "global-point-cloud.ply"
    same = vis_ply.is_file() and sha256(vis_ply) == sha256(ctx.run / "global-point-cloud.ply")
    return ok and same, detail + f"; visuals copy identical {same}"


def c18(ctx):
    bad = []
    for name, h in ctx.manifest["outputs"].items():
        if sha256(ctx.run / name) != h:
            bad.append(name)
    if set(ctx.manifest["outputs"]) != set(OUTPUTS):
        bad.append("output set")
    exr = sha256(ctx.run / "render/canonical.exr")
    if exr != ctx.meta["exr_sha256"] or ctx.manifest["inputs"]["canonical_exr"]["sha256"] != exr:
        bad.append("exr")
    if ctx.manifest["inputs"]["render_metadata"]["sha256"] != sha256(ctx.run / "render/render-metadata.json"):
        bad.append("render-metadata")
    for k, rel in (("seeds", SEEDS), ("catalog", CATALOG), ("controller02_result", C02)):
        if ctx.manifest["inputs"][k]["sha256"] != ACCEPTED[rel]:
            bad.append(k)
    for name, p in ctx.vmanifest["products"].items():
        if sha256(ctx.vis / name) != p["sha256"]:
            bad.append("visuals/" + name)
    if set(ctx.vmanifest["products"]) != set(FIGURES) | {"global-point-cloud.ply"}:
        bad.append("visual set")
    for name, h in ctx.vmanifest["sources"].items():
        if sha256(ctx.run / name) != h:
            bad.append("visual source " + name)
    return not bad, f"mismatches {bad[:6]}"


def _strings(x, path=""):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from _strings(v, f"{path}.{k}")
            yield f"{path}.{k}#key", str(k)
    elif isinstance(x, list):
        for k, v in enumerate(x):
            yield from _strings(v, f"{path}[{k}]")
    elif isinstance(x, str):
        yield path, x


def c19(ctx):
    bad = []
    docs = {"manifest": ctx.manifest, "object-stats": ctx.stats, "components": ctx.components, "seeds": ctx.seeds,
            "summary": ctx.summary, "visuals-manifest": ctx.vmanifest, "render-metadata": ctx.meta}
    for name, doc in docs.items():
        for path, s in _strings(doc):
            if "CONTROLLER-TIME" in s.upper().replace("_", "-").replace(" ", "-"):
                bad.append(f"{name}{path}")
    for name, doc in (("object-stats", ctx.stats), ("components", ctx.components), ("seeds", ctx.seeds),
                      ("summary", ctx.summary)):
        if doc.get("truth") != "DERIVED":
            bad.append(f"{name}.truth={doc.get('truth')}")
    for k, v in ctx.manifest["truth"].items():
        if not any(t in v for t in TRUTHS):
            bad.append(f"manifest.truth.{k}")
    if ctx.meta["truth"] != {"Combined": "REFERENCE / EVALUATION", "Position": "REFERENCE / EVALUATION",
                             "Object Index": "ORACLE INPUT"}:
        bad.append("render-metadata.truth")
    for name in FIGURES:
        b = ctx.vmanifest["products"].get(name, {}).get("truth_badges", [])
        if not b or not set(b) <= TRUTHS or (name in REQUIRED_BADGES and REQUIRED_BADGES[name] not in b):
            bad.append(f"badges {name} {b}")
    ply_head = (ctx.run / "global-point-cloud.ply").read_bytes()[:600].decode("ascii", "replace")
    if "CONTROLLER-TIME" in ply_head.upper():
        bad.append("ply header")
    return not bad, f"violations {bad[:5]}"


def c20(ctx):
    bad = []
    for p in ctx.processes:
        argv = p["argv"]
        script = argv[argv.index("-P") + 1] if "-P" in argv else ""
        if (p["mode"] not in ("synthetic", "preflight", "canonical") or Path(argv[0]).name != "blender"
                or not script.endswith("tools/classroom_oracle/breadth1_render.py")
                or any(re.search(r"controller0|classroom_oracle1_run|fov3d", a) for a in argv)):
            bad.append(f"process {p['mode']} {argv[:3]}")
    for name in ("actions.json", "events.json", "result.json", "final-residue.json", "evaluation.json", "objects", "bootstrap"):
        if (ctx.run / name).exists():
            bad.append(f"controller output {name}")
    for t in TOOLS:
        tree = ast.parse((REPO / t).read_text())
        for node in ast.walk(tree):
            mods = [a.name for a in node.names] if isinstance(node, ast.Import) else (
                [node.module or ""] if isinstance(node, ast.ImportFrom) else [])
            bad += [f"{t} imports {m}" for m in mods if FORBIDDEN_IMPORTS.match(m)]
    for rel, h in ACCEPTED.items():
        if sha256(SHARED / rel) != h:
            bad.append(f"source changed {rel}")
    return not bad, f"violations {bad[:5]}; {len(ctx.processes)} logged Blender invocations"


def c21(ctx):
    extra = [f for f in changed_files(ctx) if f not in BREADTH1_FILES]
    return not extra, f"undeclared changes vs {BASE[:7]}: {extra[:6]}"


def c22(ctx):
    ch = fov3d_changed(ctx)
    return not ch, f"fov3d/ changed vs {BASE[:7]}: {ch}"


def c23(ctx):
    canon = [p for p in ctx.processes if p["mode"] == "canonical"]
    ok_runs = [p for p in canon if p["returncode"] == 0]
    bad = []
    if len(ok_runs) != 1:
        bad.append(f"{len(ok_runs)} successful canonical renders")
    if ctx.meta.get("render_invocations") != 1 or ctx.meta.get("mode") != "canonical":
        bad.append("metadata invocations")
    if sha256(ctx.run / "render/canonical.exr") != ctx.meta["exr_sha256"]:
        bad.append("exr sha")
    g = ctx.glance
    if not (np.array_equal(g["instance"], ctx.instance) and np.array_equal(g["position_w"], ctx.position)
            and np.array_equal(g["rgb"], ctx.rgb)):
        bad.append("glance.npz differs from the EXR")
    if ok_runs:
        c = ok_runs[0]["code"]
        if c["dirty"] or not c["pushed"]:
            bad.append("canonical run from an uncommitted/unpushed tree")
        if ctx.preflight["code"]["commit"] != c["commit"]:
            bad.append("preflight commit")
    return not bad, "; ".join(bad) or f"one canonical render at {ok_runs[0]['code']['commit'][:7]}"


def c24(ctx):
    rec = ctx.recompute()
    cls = rec["cls"]
    acct = ctx.summary["cell_accounting"]
    wts = weights_independent()
    bad = []
    if not np.array_equal(ctx.range_npz["cell_class"], cls):
        bad.append("cell_class raster")
    for key, c in (("authored", 1), ("index0_noncatalog_geometry", 2), ("index0_no_geometry", 3)):
        m = cls == c
        if acct[key]["cells"] != int(m.sum()) or not rel_close(acct[key]["solid_angle_sr"], float(m.sum(1) @ wts), 1e-10):
            bad.append(key)
    if sum(acct[k]["cells"] for k in acct) != W * H or ctx.summary["cells_total"] != W * H:
        bad.append("total")
    return not bad, f"authored {int((cls == 1).sum())}, index-0 noncatalog {int((cls == 2).sum())}, no geometry {int((cls == 3).sum())}; {bad}"


def c25(ctx):
    s = ctx.synthetic
    canon = [p for p in ctx.processes if p["mode"] == "canonical" and p["returncode"] == 0]
    commit = canon[0]["code"]["commit"] if canon else None
    exr = ctx.run / "synthetic/synthetic.exr"
    ok = (s["passed"] and all(c["ok"] for c in s["checks"]) and len(s["checks"]) >= 25 and not s["code"]["dirty"]
          and s["code"]["commit"] == commit and exr.is_file() and sha256(exr) == s["exr_sha256"])
    return ok, f"synthetic {sum(c['ok'] for c in s['checks'])}/{len(s['checks'])} at {s['code']['commit'][:7]}"


def c26(ctx):
    sys.path.insert(0, str(HERE))
    import breadth1_visuals as V
    key = ("vis", tuple(sorted((n, sha256(ctx.run / n)) for n in ("glance.npz", "range.npz", "components.npz",
                                                                  "object-stats.json", "summary.json", "seed-directions.json"))))
    if key not in _CACHE:
        figs, _d = V.render_all(ctx.run)
        _CACHE[key] = {n: hashlib.sha256(V.png_bytes(figs[n])).hexdigest() for n in FIGURES}
    want = _CACHE[key]
    bad = [n for n in FIGURES if not (ctx.vis / n).is_file() or sha256(ctx.vis / n) != want[n]]
    return not bad, f"{len(FIGURES) - len(bad)}/{len(FIGURES)} figures regenerate byte-identically; differ {bad}"


CHECKS = [
    ("01", "canonical resolution is exactly 720 x 360", c01),
    ("02", "full-sphere camera, frozen render settings, per-cell orientation", c02),
    ("03", "fixed-head transform equals the accepted seeds.json", c03),
    ("04", "accepted catalog of exactly 234 equals the live assignment", c04),
    ("05", "rendered nonzero ids are catalog ids; Object Index integral", c05),
    ("06", "every catalog object is accounted exactly once", c06),
    ("07", "VISIBLE + NO_FIRST_HIT = 234; statuses recompute", c07),
    ("08", "spherical cell weights sum to 4 pi; independent formula", c08),
    ("09", "per-object cell counts and solid angles recompute", c09),
    ("10", "seam-aware 8-connected components recompute", c10),
    ("11", "range recomputes from Position and the cyclopean origin", c11),
    ("12", "per-object min / median / max range recompute", c12),
    ("13", "seeds lie on the largest component and reproduce the rule", c13),
    ("14", "old Controller-domain flags recompute", c14),
    ("15", "accepted-25 flags reproduce the accepted sources", c15),
    ("16", "rankings reproduce the raw supports", c16),
    ("17", "PLY point count, coordinates and ids match the canonical data", c17),
    ("18", "output hashes and manifest identities match", c18),
    ("19", "no CONTROLLER-TIME claim; every truth class declared", c19),
    ("20", "no controller executed; sources unchanged", c20),
    ("21", "accepted code unchanged: only declared Breadth-1 files changed", c21),
    ("22", "fov3d/ byte-identical to the branch base", c22),
    ("23", "exactly one canonical render; glance.npz is that EXR", c23),
    ("24", "index-0 accounting recomputes; cells total 259,200", c24),
    ("25", "synthetic plumbing test passed at the canonical commit", c25),
    ("26", "visual products regenerate byte-identically", c26),
]


def run_checks(ctx: Ctx, quiet: bool = False) -> list[dict]:
    res = []
    for num, name, fn in CHECKS:
        try:
            ok, detail = fn(ctx)
        except Exception as exc:  # a crash is a failure, never a pass
            ok, detail = False, f"{type(exc).__name__}: {exc}"
        res.append({"check": num, "name": name, "ok": bool(ok), "detail": detail})
        if not quiet:
            print(f"{PREFIX} {'PASS' if ok else 'FAIL'} {num} {name}" + ("" if ok else f" -- {detail}"))
    return res


# ------------------------------------------------------------------ corruption suite
def mirror(run: Path, vis: Path, tmp: Path) -> tuple[Path, Path]:
    def copy_tree(src: Path, dst: Path):
        for p in src.rglob("*"):
            q = dst / p.relative_to(src)
            if p.is_dir():
                q.mkdir(parents=True, exist_ok=True)
            elif p.suffix in (".json", ".jsonl", ".csv"):
                q.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(p, q)
            else:
                q.parent.mkdir(parents=True, exist_ok=True)
                q.symlink_to(p.resolve())
    r, v = tmp / "run", tmp / "vis"
    copy_tree(run, r)
    copy_tree(vis, v)
    return r, v


def edit_json(path: Path, fn) -> None:
    d = json.loads(path.read_text())
    fn(d)
    path.write_text(json.dumps(d, indent=1, sort_keys=True) + "\n")


def materialize(path: Path) -> None:
    data = path.read_bytes()
    path.unlink()
    path.write_bytes(data)


def first_visible(d):
    return min((o for o in d["objects"] if o["rank"]), key=lambda o: o["rank"])


def corruptions():
    def stats(fn):
        return lambda m, v, c: edit_json(m / "object-stats.json", fn)

    def summary(fn):
        return lambda m, v, c: edit_json(m / "summary.json", fn)

    def drop_object(d):
        d["objects"].pop()

    def drop_name(m, v, c):
        edit_json(m / "render/render-metadata.json", lambda d: d["instance_names"].pop(sorted(d["instance_names"])[0]))

    def illegal(m, v, c):
        inst = c.instance.copy(); inst[180, 360] = 999
        return {"instance": inst}

    def cells_plus(d):
        first_visible(d)["visible_cells"] += 1

    def weight(m, v, c):
        z = dict(np.load(m / "range.npz")); z["cell_weights_sr"] = z["cell_weights_sr"].copy(); z["cell_weights_sr"][10] *= 1.001
        (m / "range.npz").unlink(); np.savez_compressed(m / "range.npz", **z)

    def split_component(m, v, c):
        def fn(d):
            k = next(iter(sorted(d["objects"], key=lambda x: -len(d["objects"][x]))))
            comp = dict(d["objects"][k][0]); comp["ordinal"] = len(d["objects"][k]) + 1
            d["objects"][k].append(comp)
        edit_json(m / "components.json", fn)

    def no_wrap(m, v, c):
        """Store component counts computed without the longitude wrap (only seam-crossing objects change)."""
        forged = {}
        for oid in sorted(set(np.unique(c.instance).tolist()) - {0}):
            mask = c.instance == oid
            if not (mask[:, 0].any() and mask[:, -1].any()):
                continue
            n_flat, n_wrap = len(bfs_components(mask, False)), len(bfs_components(mask, True))
            if n_flat != n_wrap:
                forged[oid] = n_flat
        if not forged:
            return {"not_applicable": "no object crosses the longitude seam"}

        def fn(d):
            for o in d["objects"]:
                if o["instance_id"] in forged:
                    o["components"] = forged[o["instance_id"]]
        edit_json(m / "object-stats.json", fn)

        def fc(d):
            for oid, n in forged.items():
                comps = d["objects"][str(oid)]
                while len(comps) < n:
                    comps.append(dict(comps[-1], ordinal=len(comps) + 1))
        edit_json(m / "components.json", fc)

    def seed_off(m, v, c):
        d = json.loads((m / "seed-directions.json").read_text())
        s = d["seeds"][0]
        oid = s["instance_id"]
        rr, cc = np.nonzero(c.instance != oid)
        k = int(np.argmin((rr - s["row"]) ** 2 + ((cc - s["col"] + W // 2) % W - W // 2) ** 2))
        s["row"], s["col"] = int(rr[k]), int(cc[k])
        (m / "seed-directions.json").write_text(json.dumps(d))

    def seed_other_tie(m, v, c):
        """Move one seed to another numerically tied cell: on support, on the largest component, equally near
        the mean; only the declared tie-break (smaller row, then column) rejects it."""
        rec = c.recompute()["objs"]
        wts = weights_independent()
        yc, pc = centres()
        dirs = unit(*np.meshgrid(yc, pc))
        for oid in sorted(rec):
            v_ = rec[oid]
            if not v_["cells"] or (v_["tied"] or 0) < 2:
                continue
            big = v_["comps"][0]
            dd = dirs[big["rows"], big["cols"]]
            mu = (dd * wts[big["rows"]][:, None]).sum(0); mu /= np.linalg.norm(mu)
            dots = dd @ mu
            tied = sorted((int(big["rows"][k]), int(big["cols"][k])) for k in np.flatnonzero(dots.max() - dots <= SEED_TIE_DOT_EPS))
            other = tied[-1]
            for name in ("seed-directions.json", "object-stats.json"):
                d = json.loads((m / name).read_text())
                for s in (d["seeds"] if name.startswith("seed") else [o["seed"] for o in d["objects"] if o["instance_id"] == oid]):
                    if s is not None and s.get("instance_id", oid) == oid:
                        s["row"], s["col"] = other
                        s["yaw_deg"], s["pitch_deg"] = float(yc[other[1]]), float(pc[other[0]])
                (m / name).write_text(json.dumps(d))
            return {"note": f"object {oid}: {tied[0]} -> {other}"}
        return {"not_applicable": "no numerically tied seed"}

    def median(d):
        first_visible(d)["range_m"]["median"] += 0.01

    def flip_domain(d):
        o = first_visible(d); o["intersects_old_controller_domain"] = not o["intersects_old_controller_domain"]

    def flip_25(d):
        o = first_visible(d); o["in_accepted_localized_25"] = not o["in_accepted_localized_25"]

    def ply_short(m, v, c):
        p = m / "global-point-cloud.ply"
        data = p.read_bytes()
        end = data.index(b"end_header\n") + len(b"end_header\n")
        n = int(re.search(rb"element vertex (\d+)", data[:end]).group(1))
        head = data[:end].replace(f"element vertex {n}".encode(), f"element vertex {n - 1}".encode())
        p.unlink(); p.write_bytes(head + data[end:-22])

    def provenance(d):
        d["truth"] = "CONTROLLER-TIME"

    def cfg_spp(m, v, c):
        edit_json(m / "render/render-metadata.json", lambda d: d["config"].update(samples=256))

    def cfg_res(m, v, c):
        edit_json(m / "render/render-metadata.json", lambda d: d["config"].update(resolution_wh=[640, 320]))

    def flip_cols(m, v, c):
        return {"position": c.position[:, ::-1].copy()}

    def head(m, v, c):
        edit_json(m / "render/render-metadata.json", lambda d: d["head_R_wh_requested"][0].__setitem__(0, 0.999))

    def swap_rank(d):
        a = min((o for o in d["objects"] if o["rank"]), key=lambda o: o["rank"])
        b = next(o for o in d["objects"] if o["rank"] == a["rank"] + 1)
        a["rank"], b["rank"] = b["rank"], a["rank"]

    def manifest_hash(m, v, c):
        edit_json(m / "manifest.json", lambda d: d["outputs"].update({"summary.json": "0" * 64}))

    def controller_proc(m, v, c):
        with open(m / "process-log.jsonl", "a") as f:
            f.write(json.dumps({"mode": "canonical", "returncode": 0, "argv": [
                "python", "fov3d/experiments/classroom_oracle/controller02.py"], "code": c.processes[-1]["code"]}) + "\n")

    def tool_changed(m, v, c):
        return {"changed_files": changed_files(c) + ["tools/controller/check_controller02.py"]}

    def fov3d(m, v, c):
        return {"fov3d_changed": True}

    def second_render(m, v, c):
        canon = next(p for p in c.processes if p["mode"] == "canonical")
        with open(m / "process-log.jsonl", "a") as f:
            f.write(json.dumps(canon) + "\n")

    def index0(d):
        d["cell_accounting"]["index0_no_geometry"]["cells"] += 1

    def visible_count(d):
        d["visible_at_0p5_deg"] += 1

    def range_raster(m, v, c):
        z = dict(np.load(m / "range.npz")); r = z["range_m"].copy(); k = np.argwhere(np.isfinite(r))[0]
        r[tuple(k)] += 0.05; z["range_m"] = r
        (m / "range.npz").unlink(); np.savez_compressed(m / "range.npz", **z)

    def synthetic_failed(m, v, c):
        edit_json(m / "synthetic/synthetic-report.json", lambda d: d["checks"][0].update(ok=False))

    def png_pixel(m, v, c):
        p = v / "overview.png"
        from PIL import Image
        img = Image.open(p.resolve()).convert("RGB"); img.putpixel((5, 5), (255, 0, 0))
        p.unlink(); img.save(p)

    return [
        ("wrong catalog count (an object record dropped)", "06", stats(drop_object)),
        ("wrong catalog count (live assignment 233)", "04", drop_name),
        ("illegal instance id 999", "05", illegal),
        ("altered visible-support count", "09", stats(cells_plus)),
        ("wrong spherical row weight", "08", weight),
        ("broken seam/component count", "10", split_component),
        ("components counted without the longitude wrap", "10", no_wrap),
        ("seed moved off support", "13", seed_off),
        ("seed moved to another numerically tied cell (tie-break)", "13", seed_other_tie),
        ("altered range statistic", "12", stats(median)),
        ("flipped old-domain flag", "14", stats(flip_domain)),
        ("flipped accepted-25 flag", "15", stats(flip_25)),
        ("wrong PLY point count", "17", ply_short),
        ("false provenance class", "19", summary(provenance)),
        ("changed render configuration (spp 256)", "02", cfg_spp),
        ("changed render configuration (640 x 320)", "01", cfg_res),
        ("flipped image columns", "02", flip_cols),
        ("altered head transform", "03", head),
        ("swapped ranks", "16", stats(swap_rank)),
        ("altered manifest hash", "18", manifest_hash),
        ("controller command in the process log", "20", controller_proc),
        ("changed accepted tool", "21", tool_changed),
        ("changed fov3d file", "22", fov3d),
        ("second canonical render", "23", second_render),
        ("altered index-0 count", "24", summary(index0)),
        ("V + N inconsistent", "07", summary(visible_count)),
        ("altered range raster", "11", range_raster),
        ("synthetic test failed", "25", synthetic_failed),
        ("overview pixel altered", "26", png_pixel),
    ]


def corruption_suite(run: Path, vis: Path) -> tuple[int, int]:
    caught = total = 0
    results = []
    suite = corruptions()
    for name, target, fn in suite:
        with tempfile.TemporaryDirectory(prefix="breadth1-corrupt-") as td:
            m, v = mirror(run, vis, Path(td))
            overrides = fn(m, v, Ctx(m, v)) or {}   # file corruptions edit the mirror; mutants return overrides
            if "not_applicable" in overrides:
                print(f"{PREFIX} corruption N/A [{target}] {name}: {overrides['not_applicable']}")
                continue
            total += 1
            note = overrides.pop("note", "")
            ctx = Ctx(m, v)
            for attr, value in overrides.items():
                setattr(ctx, attr, value)
            with contextlib.redirect_stdout(io.StringIO()):
                res = run_checks(ctx, quiet=True)
            failed = {r["check"] for r in res if not r["ok"]}
            hit = target in failed
            caught += hit
            results.append({"name": name, "target": target, "caught": bool(hit), "failed": sorted(failed), "note": note})
            print(f"{PREFIX} corruption {'CAUGHT' if hit else 'MISSED'} [{target}] {name}"
                  + (f" ({note})" if note else "") + f" (failed: {sorted(failed)})")
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
    print(f"{PREFIX} SUMMARY checked={len(res)} failed={len(res) - npass}")
    ok = npass == len(res)
    if ok:
        print(f"{PREFIX} BREADTH1_CHECKS_PASS")
    out = {"schema": "Breadth1-check-summary-v1", "checks": res, "passed": ok, "code": git("rev-parse", "HEAD").strip()}
    if a.corruptions:
        caught, total, results = corruption_suite(run, vis)
        probative = ok  # a corruption only demonstrates its check when the uncorrupted baseline passes
        out["corruptions"] = {"caught": caught, "total": total, "baseline_passing": probative, "results": results}
        print(f"{PREFIX} CORRUPTIONS caught={caught}/{total}" + ("" if probative else " (NOT PROBATIVE: baseline failing)"))
        if caught == total and probative:
            print(f"{PREFIX} BREADTH1_MUTATIONS_CAUGHT")
        ok = ok and caught == total
    if a.write_summary:
        (run / "check-summary.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
