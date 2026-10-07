"""Greedy Foveal Explorer, official baseline: the presentation demo (OFFLINE REPLAY of the frozen grow600 run;
presentation only).

The demo record is docs/prototype/greedy-foveal-explorer-v0-demo.md on tag greedy-foveal-explorer-v0-demo.  Nothing here
changes the run, the explorer or any measured product; the run's freeze is verified before anything is read.

    .venv/bin/python tools/greedy_foveal/demo.py rerender   # post-hoc display RGB of every fixation (cached, 64 spp)
    .venv/bin/python tools/greedy_foveal/demo.py build      # derived assets -> reference assets -> video -> stills
    .venv/bin/python tools/greedy_foveal/demo.py check

``rerender`` drives the unchanged render server (``run.Server`` / ``render_server.py``) at each fixation's saved gaze;
the calibration it writes must be byte-identical to the saved one, and the re-rendered left Position must reproduce
the saved reconstructed points (a same-view check).  Only the left / right foveal RGB is kept (display only).
``build`` keeps the truth domains in separate audited stages: the DERIVED panels (eyes, depth, observer state, 3-D map,
final reconstructed panoramas) are computed from run products before any reference file is opened; the Breadth-1
reference enters only the panels labelled REFERENCE.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
for _p in (HERE, HERE.parent, HERE.parent / "visual_language", HERE.parent / "classroom_oracle"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import explorer as X  # noqa: E402
import fsg_geometry as FG  # noqa: E402
import style as S  # noqa: E402  (Visual Language 1)
from exr_lite import read_uncompressed_exr  # noqa: E402
from visuals import dashed_polyline, display_rgb, oracle_colors  # noqa: E402

SHARED = Path("/home/lvelho/rd/f3d-vision")
RUN = SHARED / "previews/greedy-foveal-explorer-v0-grow600"
CACHE = SHARED / "previews/greedy-foveal-explorer-v0-demo-cache"
OUT = SHARED / "visuals/greedy-foveal-explorer-v0-demo"
B1_EXR = SHARED / "previews/breadth-1-classroom-234-spherical-glance/render/canonical.exr"
B1_EXR_SHA256 = "4ea036fc74eab3b3ab06a0c4470c2b01740c9322de0eea522f957ddfffa172f8"
SPP = 64
CORE = slice(X.CORE_ORIGIN, X.CORE_ORIGIN + X.CORE_SIZE)
PREFIX = "[gfe-demo]"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path: Path):
    return json.loads(Path(path).read_text())


def write_json(path: Path, data) -> None:
    Path(path).write_text(json.dumps(data, indent=1, sort_keys=True) + "\n")


class Audit:
    """Which files each stage opens (Python-level opens; enough for this presentation firewall)."""

    def __init__(self) -> None:
        self.stage: str | None = None
        self.opens: dict[str, set[str]] = {}

    def hook(self, event: str, args) -> None:
        if self.stage and event == "open" and args and isinstance(args[0], (str, bytes, os.PathLike)):
            p = os.fsdecode(args[0])
            if not p.endswith((".py", ".pyc", ".ttf")) and "/site-packages/" not in p and "/lib/python" not in p:
                self.opens.setdefault(self.stage, set()).add(p)


AUDIT = Audit()
sys.addaudithook(AUDIT.hook)


def verify_run() -> dict:
    fz = read_json(RUN / "freeze.json")
    for f, h in fz["files"].items():
        if sha256(RUN / f) != h:
            raise SystemExit(f"{PREFIX} STOP {f} differs from the run freeze")
    return fz


def exr_rgb_pos(path: Path, position: bool) -> dict:
    ch = read_uncompressed_exr(str(path))

    def one(suffix: str) -> np.ndarray:
        keys = [k for k in ch if k.endswith(suffix)]
        if len(keys) != 1:
            raise RuntimeError(f"expected one EXR channel ending {suffix!r}, got {keys}")
        return np.asarray(ch[keys[0]])

    out = {"rgb": np.stack([one(f"Combined.{c}") for c in "RGB"], -1).astype(np.float32)}
    if position:
        out["pos"] = np.stack([one(f"Position.{c}") for c in "XYZ"], -1).astype(np.float64)
    return out


def left_pixels(c: dict, xyz: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Raw left-eye pixel (row, col) of each reconstructed point (its left ray passes through that pixel centre)."""
    uv, _ = FG.project_h(c["eyes"][0], np.asarray(xyz, np.float64))
    return np.rint(uv[:, 1]).astype(np.int64), np.rint(uv[:, 0]).astype(np.int64)


# ================================================================== stage 1: the post-hoc display re-render
def rerender(a) -> None:
    import run as R                                   # the unchanged run machinery (render server driver)
    verify_run()
    T = read_json(RUN / "trajectory.json")["trajectory"]
    eyes = CACHE / "eyes"
    eyes.mkdir(parents=True, exist_ok=True)
    man_p = CACHE / "eyes-manifest.json"
    man = read_json(man_p) if man_p.exists() else {"fixations": {}}
    todo = [e for e in T if not (eyes / f"fix-{e['n']:04d}.npz").exists()]
    print(f"{PREFIX} re-render {len(todo)} of {len(T)} fixations at {SPP} spp", flush=True)
    if not todo:
        return
    srv = CACHE / f"render-{time.strftime('%Y%m%d-%H%M%S')}"
    server = R.Server(srv, SPP)
    man["server"] = {k: server.ready[k] for k in ("blender", "device", "spp", "seeds")}
    t_start = time.perf_counter()
    try:
        for i, e in enumerate(todo, 1):
            k = e["n"]
            out = srv / "fix" / f"{k:04d}"
            done = server.render(i, e["yaw_deg"], e["pitch_deg"], out)
            saved = (RUN / f"fixations/fix-{k:04d}/calibration.json").read_bytes()
            if (out / "calibration.json").read_bytes() != saved:
                raise SystemExit(f"{PREFIX} STOP fixation {k}: re-render calibration differs from the saved one")
            c = json.loads(saved)
            L, Rr = exr_rgb_pos(out / "raw_L.exr", True), exr_rgb_pos(out / "raw_R.exr", False)
            with np.load(RUN / f"fixations/fix-{k:04d}/points.npz") as z:
                xyz = z["xyz_h"].astype(np.float64)
            same = None
            if len(xyz):
                r, cc = left_pixels(c, xyz)
                ok = (r >= 0) & (r < L["pos"].shape[0]) & (cc >= 0) & (cc < L["pos"].shape[1])
                ph = FG.world_to_head(c, L["pos"][r[ok], cc[ok]])
                d = np.linalg.norm(ph - xyz[ok], axis=1) * 1e3
                same = {"median_mm": float(np.median(d)), "p95_mm": float(np.quantile(d, 0.95)),
                        "inside": int(ok.sum()), "points": int(len(xyz))}
            np.savez_compressed(eyes / f"fix-{k:04d}.npz", left=display_rgb(L["rgb"][CORE, CORE]),
                                right=display_rgb(Rr["rgb"][CORE, CORE]))
            man["fixations"][str(k)] = {"calibration_identical": True, "render_seconds_lr": done["render_seconds_lr"],
                                        "same_view_vs_saved_points": same}
            for s in "LR":
                (out / f"raw_{s}.exr").unlink()
            if i % 25 == 0 or i == len(todo):
                write_json(man_p, man)
                el = time.perf_counter() - t_start
                print(f"{PREFIX} {i}/{len(todo)} (fixation {k}) {el:.0f} s; same-view median "
                      f"{same['median_mm'] if same else float('nan'):.3f} mm", flush=True)
    finally:
        server.stop()
        write_json(man_p, man)


# ================================================================== presentation constants and helpers
W, H, FPS = 1920, 1080, 30
STRIP_H = 72
PW, PH = 960, 504                                  # one quadrant
EQ_W, EQ_H = 896, 448                              # equirectangular panels
EQ_POS = (32, 46)
C_LOCAL, C_GLOBAL = S.OI_BLUE, S.OI_VERM
C_UNSEEN, C_SEEN, C_DEPTH = (236, 235, 230), (166, 196, 222), (0, 92, 150)
C_UNKNOWN = (232, 229, 222)
C_TINT = 0.36                                      # panel C: own RGB tinted toward DEPTH blue
TRAIL_DECAY, TRAIL_FLOOR = 0.95, 50                # panel A: recent saccades strong, older ones faint
PANEL_D_VIEW = (90.0, 40.0)                        # azimuth / elevation (deg) of the panel-D camera
BG3D = (252, 252, 250)
BLUES = [(198, 219, 239), (158, 202, 225), (107, 174, 214), (66, 146, 198), (33, 113, 181), (8, 81, 156), (8, 48, 107)]
DMIN, DMAX = 0.5, 5.5                              # display depth scale (m), shared by every depth image
CEIL = 0.3                                         # 3-D views: keep head-frame Y <= 0.3 m (ceiling removed)
VOX_PANEL, VOX_ORBIT = 0.015, 0.010
REF_RGB_REL = "reference/b1-rgb.png"               # the ONLY reference file the replay video may open


def depth_colors(r) -> np.ndarray:
    t = np.clip((np.asarray(r, np.float64) - DMIN) / (DMAX - DMIN), 0.0, 1.0)
    lut = np.asarray(BLUES, np.float64)
    xs = np.linspace(0.0, 1.0, len(BLUES))
    return np.stack([np.interp(t, xs, lut[:, i]) for i in range(3)], -1).astype(np.uint8)


def tag(img: Image.Image, x: float, y: float, label: str, kind: str, size: int = 15, right: bool = False) -> list:
    """A Visual Language 1 truth tag with free text: controller (filled blue), derived (dashed), reference (hatched
    brown), oracle (double outline, wine), global (filled vermilion)."""
    d = ImageDraw.Draw(img)
    f = S.font(size, True)
    w, h = d.textlength(label, font=f) + 22, size + 12
    x0 = x - w if right else x
    box = [x0, y, x0 + w, y + h]
    if kind in ("controller", "global", "local", "stop"):
        col = {"controller": S.OI_BLUE, "global": C_GLOBAL, "local": C_LOCAL, "stop": S.INK}[kind]
        d.rounded_rectangle(box, radius=6, fill=col)
        d.text((box[0] + 11, y + 5), label, font=f, fill=S.WHITE)
    elif kind == "derived":
        d.rounded_rectangle(box, radius=6, fill=S.WHITE)
        S.dashed_rect(d, box, S.INK2, width=2, dash=7, gap=5)
        d.text((box[0] + 11, y + 5), label, font=f, fill=S.INK2)
    elif kind == "reference":
        d.rounded_rectangle(box, radius=6, fill=(246, 238, 222))
        S.hatch(img, box, (224, 205, 170), spacing=8, width=2)
        d = ImageDraw.Draw(img)
        d.rounded_rectangle(box, radius=6, outline=S.REF_BROWN, width=2)
        tb = d.textbbox((box[0] + 11, y + 5), label, font=f)
        d.rectangle([tb[0] - 3, tb[1] - 1, tb[2] + 3, tb[3] + 1], fill=(246, 238, 222))
        d.text((box[0] + 11, y + 5), label, font=f, fill=S.REF_BROWN)
    else:  # oracle
        d.rounded_rectangle(box, radius=6, fill=S.WHITE, outline=S.WINE, width=2)
        d.rounded_rectangle([box[0] + 4, box[1] + 4, box[2] - 4, box[3] - 4], radius=4, outline=S.WINE, width=1)
        d.text((box[0] + 11, y + 5), label, font=f, fill=S.WINE)
    return box


def eq_xy(yaw, pitch, w: int, h: int):
    return (np.asarray(yaw) + 180.0) / 360.0 * w, (90.0 - np.asarray(pitch)) / 180.0 * h


def eq_runs(dirs: np.ndarray, w: int, h: int) -> list[list[tuple[float, float]]]:
    yaw, pitch = X.yaw_pitch(dirs)
    xs, ys = eq_xy(yaw, pitch, w, h)
    runs, cur = [], [(float(xs[0]), float(ys[0]))]
    for k in range(1, len(xs)):
        if abs(xs[k] - xs[k - 1]) > w / 2:
            runs.append(cur)
            cur = []
        cur.append((float(xs[k]), float(ys[k])))
    runs.append(cur)
    return [r for r in runs if len(r) > 1]


def arc(a: np.ndarray, b: np.ndarray, step_deg: float = 0.5) -> np.ndarray:
    om = math.acos(float(np.clip(a @ b, -1.0, 1.0)))
    if om < 1e-9:
        return np.vstack([a, b])
    t = np.linspace(0.0, 1.0, max(2, int(math.degrees(om) / step_deg) + 2))[:, None]
    return (np.sin((1 - t) * om) * a + np.sin(t * om) * b) / math.sin(om)


def footprint_dirs(yaw: float, pitch: float, n: int = 24) -> np.ndarray:
    r = X.frame(yaw, pitch)
    t = math.tan(math.radians(X.CORE_FOV_DEG / 2))
    s = np.linspace(-t, t, n)
    uv = np.concatenate([np.stack([s, -t + 0 * s], 1), np.stack([t + 0 * s, s], 1),
                         np.stack([s[::-1], t + 0 * s], 1), np.stack([-t + 0 * s, s[::-1]], 1)])
    d = r[:, 2] + uv[:, :1] * r[:, 0] + uv[:, 1:] * r[:, 1]
    return d / np.linalg.norm(d, axis=1, keepdims=True)


def draw_runs(d, runs, color, width, dashed=False, halo=True, ox=0, oy=0):
    for r in runs:
        pts = [(x + ox, y + oy) for x, y in r]
        if halo:
            if dashed:
                dashed_polyline(d, pts, S.WHITE, width=width + 4)
            else:
                d.line(pts, fill=S.WHITE, width=width + 4)
        if dashed:
            dashed_polyline(d, pts, color, width=width)
        else:
            d.line(pts, fill=color, width=width)


def equirect_splat(xyz: np.ndarray, w: int, h: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Nearest-range sample per equirectangular pixel: (flat pixel ids, chosen point ids, ranges)."""
    xyz = np.asarray(xyz, np.float64)
    yaw, pitch = X.yaw_pitch(xyz)
    rng = np.linalg.norm(xyz, axis=1)
    u = np.floor((yaw + 180.0) / 360.0 * w).astype(np.int64) % w
    v = np.clip(np.floor((90.0 - pitch) / 180.0 * h).astype(np.int64), 0, h - 1)
    pix = v * w + u
    order = np.lexsort((rng, pix))
    first = np.unique(pix[order], return_index=True)[1]
    idx = order[first]
    return pix[idx], idx, rng[idx]


def stipple_mask(h: int, w: int, spacing: int = 7) -> np.ndarray:
    m = np.zeros((h, w), bool)
    for yy in range(spacing // 2, h, spacing):
        off = spacing // 2 if (yy // spacing) % 2 else 0
        m[yy, off::spacing] = True
    return m


def panorama_image(pix, colors, w, h) -> np.ndarray:
    img = np.empty((h * w, 3), np.uint8)
    img[:] = C_UNKNOWN
    img[pix] = colors
    img = img.reshape(h, w, 3)
    unk = np.ones(h * w, bool)
    unk[pix] = False
    img[unk.reshape(h, w) & stipple_mask(h, w, 9)] = S.STIPPLE
    return img


def voxelize(xyz, rgb_u8, first, size: float) -> dict:
    """Display downsample of run geometry: per voxel the mean position / colour and the EARLIEST creating fixation."""
    k = np.floor(np.asarray(xyz) / size).astype(np.int64)
    k -= k.min(0)
    key = (k[:, 0] << 42) | (k[:, 1] << 21) | k[:, 2]
    uk, inv = np.unique(key, return_inverse=True)
    cnt = np.bincount(inv).astype(np.float64)
    cen = np.stack([np.bincount(inv, xyz[:, i]) for i in range(3)], 1) / cnt[:, None]
    col = np.stack([np.bincount(inv, rgb_u8[:, i].astype(np.float64)) for i in range(3)], 1) / cnt[:, None]
    fst = np.full(len(uk), np.iinfo(np.int32).max, np.int64)
    np.minimum.at(fst, inv, np.asarray(first, np.int64))
    o = np.argsort(fst, kind="stable")
    return {"xyz": cen[o], "rgb": np.rint(col[o]).astype(np.uint8), "first": fst[o], "count": cnt[o].astype(np.int64)}


class Camera:
    """A pinhole looking at the room from above / behind (head frame: +X right, +Y up, -Z forward)."""

    def __init__(self, target, azim_deg: float, elev_deg: float, dist: float, f: float, cx: float, cy: float):
        a, e = math.radians(azim_deg), math.radians(elev_deg)
        self.eye = np.asarray(target, float) + dist * np.array([math.sin(a) * math.cos(e), math.sin(e),
                                                                math.cos(a) * math.cos(e)])
        fw = np.asarray(target, float) - self.eye
        fw /= np.linalg.norm(fw)
        rt = np.cross(fw, [0.0, 1.0, 0.0])
        rt /= np.linalg.norm(rt)
        dn = np.cross(fw, rt)
        self.R = np.stack([rt, dn, fw])                # rows: image right, image down, forward
        self.f, self.cx, self.cy = f, cx, cy

    def project(self, p):
        pc = (np.asarray(p, np.float64) - self.eye) @ self.R.T
        z = pc[..., 2]
        return self.f * pc[..., 0] / z + self.cx, self.f * pc[..., 1] / z + self.cy, z

    @staticmethod
    def fitted(points, w, h, azim, elev, dist, margin=0.06, target=None):
        target = np.asarray(points).mean(0) if target is None else target
        c = Camera(target, azim, elev, dist, 1.0, 0.0, 0.0)
        x, y, z = c.project(points)
        lo = np.percentile(np.stack([x, y], 1), 0.3, axis=0)
        hi = np.percentile(np.stack([x, y], 1), 99.7, axis=0)
        f = min(w * (1 - 2 * margin) / (hi[0] - lo[0]), h * (1 - 2 * margin) / (hi[1] - lo[1]))
        return Camera(target, azim, elev, dist, f, w / 2 - f * (lo[0] + hi[0]) / 2, h / 2 - f * (lo[1] + hi[1]) / 2)


SPLAT = np.array([(0, 0), (1, 0), (0, 1), (1, 1)], np.int64)


def zsplat(img: np.ndarray, zbuf: np.ndarray, px, py, z, col) -> np.ndarray:
    """Splat 2 x 2 squares, nearest wins (incremental z-buffer); returns the flat pixels that changed."""
    h, w = zbuf.shape
    px = np.rint(px).astype(np.int64)
    py = np.rint(py).astype(np.int64)
    X_ = (px[:, None] + SPLAT[None, :, 0]).ravel()
    Y_ = (py[:, None] + SPLAT[None, :, 1]).ravel()
    Z_ = np.repeat(z, len(SPLAT))
    C_ = np.repeat(col, len(SPLAT), axis=0)
    ok = (X_ >= 0) & (X_ < w) & (Y_ >= 0) & (Y_ < h) & (Z_ > 0.1)
    flat = Y_[ok] * w + X_[ok]
    Z_, C_ = Z_[ok], C_[ok]
    zb = zbuf.reshape(-1)
    win = Z_ < zb[flat]
    flat, Z_, C_ = flat[win], Z_[win], C_[win]
    o = np.argsort(-Z_, kind="stable")                    # far first, nearest written last
    zb[flat[o]] = Z_[o]
    img.reshape(-1, 3)[flat[o]] = C_[o]
    return np.unique(flat)


def render_points(xyz, col, cam: Camera, w: int, h: int, bg=BG3D) -> np.ndarray:
    img = np.empty((h, w, 3), np.uint8)
    img[:] = bg
    zbuf = np.full((h, w), np.inf)
    x, y, z = cam.project(xyz)
    zsplat(img, zbuf, x, y, z, col)
    return img


# ================================================================== stage 2a: DERIVED assets (run products only)
def derived_assets(T: list[dict]) -> dict:
    with np.load(RUN / "final-map.npz") as z:
        m = {k: np.array(z[k]) for k in ("xyz_h", "rgb", "instance_id_oracle", "first_fixation", "support_count")}
    xyz = m["xyz_h"]
    rgb8 = display_rgb(m["rgb"])
    pw, ph = 1440, 720                             # 0.25 deg per pixel
    pix, idx, rng = equirect_splat(xyz, pw, ph)
    pano = {"rgb": panorama_image(pix, rgb8[idx], pw, ph),
            "depth": panorama_image(pix, depth_colors(rng), pw, ph),
            "instance": panorama_image(pix, oracle_colors(m["instance_id_oracle"][idx]), pw, ph)}
    for k, v in pano.items():
        Image.fromarray(v).save(OUT / f"final-{k}-panorama.png", optimize=True)
    keep = xyz[:, 1] <= CEIL
    vp = voxelize(xyz[keep], rgb8[keep], m["first_fixation"][keep], VOX_PANEL)
    vo = voxelize(xyz[keep], rgb8[keep], m["first_fixation"][keep], VOX_ORBIT)
    lo, hi = np.percentile(xyz[keep], 0.5, axis=0), np.percentile(xyz[keep], 99.5, axis=0)
    target = np.array([(lo[0] + hi[0]) / 2, lo[1], (lo[2] + hi[2]) / 2])
    print(f"{PREFIX} derived: {len(xyz):,d} surfels, panel voxels {len(vp['xyz']):,d}, orbit voxels "
          f"{len(vo['xyz']):,d}, panorama pixels {len(pix):,d}", flush=True)
    return {"map": m, "rgb8": rgb8, "keep": keep, "pano": pano, "vox_panel": vp, "vox_orbit": vo, "target": target,
            "map_sha256": sha256(RUN / "final-map.npz")}


def depth_patch(c: dict, xyz: np.ndarray) -> np.ndarray:
    """The fixation's DERIVED metric depth on the left foveal grid (range from the left eye), from saved points."""
    img = np.empty((X.CORE_SIZE, X.CORE_SIZE, 3), np.uint8)
    img[:] = C_UNKNOWN
    if len(xyz):
        r, cc = left_pixels(c, xyz)
        r, cc = r - X.CORE_ORIGIN, cc - X.CORE_ORIGIN
        ok = (r >= 0) & (r < X.CORE_SIZE) & (cc >= 0) & (cc < X.CORE_SIZE)
        rng = np.linalg.norm(xyz - np.asarray(c["eyes"][0]["centre_h_m"]), axis=1)
        img[r[ok], cc[ok]] = depth_colors(rng[ok])
    return img


# ================================================================== stage 2b: REFERENCE assets (Breadth-1; evaluation)
def reference_assets(ev: dict) -> dict:
    import breadth1_glance as BG1
    if sha256(B1_EXR) != B1_EXR_SHA256:
        raise SystemExit(f"{PREFIX} STOP the Breadth-1 EXR is not the accepted one")
    ex = BG1.extract_exr(B1_EXR)
    c1 = read_json(RUN / "fixations/fix-0001/calibration.json")
    hr, ho = np.asarray(c1["head_R_wh"]), np.asarray(c1["head_origin_w_m"])
    pos, inst = ex["position_w"].astype(np.float64), ex["instance"]
    hit = np.isfinite(pos).all(-1) & ~np.all(pos == 0.0, axis=-1)
    rng = np.linalg.norm(BG1.head_points(pos, hr, ho), axis=-1)
    h, w = inst.shape
    rgb = display_rgb(ex["rgb"])
    dep = depth_colors(rng)
    dep[~hit] = C_UNKNOWN
    ins = oracle_colors(inst.reshape(-1)).reshape(h, w, 3)
    ins[~hit] = C_UNKNOWN
    with np.load(RUN / "evaluation.npz") as z:
        rc, covered = z["cells_rc"].astype(np.int64), z["covered"]
    cov = np.empty((h, w, 3), np.uint8)
    cov[:] = S.WHITE
    cov[rc[:, 0], rc[:, 1]] = np.where(covered[:, None], np.array(S.CORE_GREEN), np.array((222, 220, 214)))
    (CACHE / "reference").mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgb).save(CACHE / REF_RGB_REL)
    out = {"rgb": rgb, "depth": dep, "instance": ins, "coverage": cov}
    for k in ("rgb", "depth", "instance"):
        Image.fromarray(out[k]).save(OUT / f"reference-{k}-panorama.png", optimize=True)
    return out


# ================================================================== the replay frame
class Replay:
    def __init__(self, T: list[dict], D: dict, ref_rgb: np.ndarray):
        self.T, self.D, self.N = T, D, len(T)
        bg = Image.fromarray(ref_rgb).resize((EQ_W, EQ_H), Image.BICUBIC)
        self.a_bg = Image.blend(bg, Image.new("RGB", bg.size, S.WHITE), 0.22)
        self.traj = Image.new("RGBA", (EQ_W, EQ_H), (0, 0, 0, 0))
        self.dirs = X.direction(np.array([e["yaw_deg"] for e in T]), np.array([e["pitch_deg"] for e in T]))
        self.c_rgb = np.zeros((EQ_H, EQ_W, 3), np.uint8)
        self.c_have = np.zeros((EQ_H, EQ_W), bool)
        self.c_z = np.full(EQ_H * EQ_W, np.inf)
        self.c_dots = stipple_mask(EQ_H, EQ_W, 7)
        self.c_r = (np.arange(EQ_H) * X.H) // EQ_H
        self.c_c = (np.arange(EQ_W) * X.W) // EQ_W
        vp = D["vox_panel"]
        self.cam = Camera.fitted(vp["xyz"], EQ_W, EQ_H, azim=PANEL_D_VIEW[0], elev=PANEL_D_VIEW[1], dist=14.0, margin=0.03,
                                 target=D["target"])
        self.vx, self.vy, self.vz = self.cam.project(vp["xyz"])
        self.vfirst = vp["first"]
        self.d_img = np.empty((EQ_H, EQ_W, 3), np.uint8)
        self.d_img[:] = BG3D
        self.d_z = np.full((EQ_H, EQ_W), np.inf)
        self.static = self._static()

    # ---------------- static chrome
    def _static(self) -> Image.Image:
        img = Image.new("RGB", (W, H), S.SURFACE)
        d = ImageDraw.Draw(img)
        d.line([0, STRIP_H, W, STRIP_H], fill=S.FAINT, width=2)
        d.line([PW, STRIP_H, PW, H], fill=S.FAINT, width=2)
        d.line([0, STRIP_H + PH, W, STRIP_H + PH], fill=S.FAINT, width=2)
        titles = {"A": ("A · 360° CLASSROOM AND GAZE", 0, STRIP_H), "B": ("B · CURRENT FOVEAL OBSERVATION (12° fovea)", PW,
                                                                        STRIP_H),
                  "C": ("C · OBSERVER'S 360° STATE", 0, STRIP_H + PH),
                  "D": ("D · PERSISTENT 3-D SCENE MEMORY (H0)", PW, STRIP_H + PH)}
        for _k, (t, x, y) in titles.items():
            S.text(d, (x + 32, y + 12), t, size=20, bold=True, outline=None)
        tag(img, PW - 30, STRIP_H + 8, "REFERENCE / PRESENTATION · NOT AVAILABLE TO CONTROLLER", "reference",
            size=13, right=True)
        tag(img, PW - 30, STRIP_H + PH + 8, "CONTROLLER-TIME", "controller", size=13, right=True)
        tag(img, W - 30, STRIP_H + PH + 8, "DERIVED · DISPLAY DOWNSAMPLE", "derived", size=13, right=True)
        # panel C legend (in its title bar)
        x = 380
        for lab, col in (("UNSEEN", C_UNSEEN), ("SEEN", C_SEEN), ("DEPTH (own RGB, blue tint)", C_DEPTH)):
            y = STRIP_H + PH + 14
            d.rectangle([x, y, x + 22, y + 16], fill=col, outline=S.FAINT)
            S.text(d, (x + 28, y - 1), lab, size=14, outline=None)
            x += 36 + d.textlength(lab, font=S.font(14))
        return img

    # ---------------- per-fixation state updates
    def advance(self, k: int) -> dict:
        e = self.T[k - 1]
        with np.load(RUN / f"fixations/fix-{k:04d}/points.npz") as z:
            xyz = z["xyz_h"].astype(np.float64)
            rgb = z["rgb"]
        cal = read_json(RUN / f"fixations/fix-{k:04d}/calibration.json")
        # C: the observer's own measured RGB on the sphere (nearest range per pixel)
        if len(xyz):
            pix, idx, rng = equirect_splat(xyz, EQ_W, EQ_H)
            win = rng < self.c_z[pix]
            self.c_z[pix[win]] = rng[win]
            self.c_rgb.reshape(-1, 3)[pix[win]] = display_rgb(rgb[idx[win]])
            self.c_have.reshape(-1)[pix[win]] = True
        st_p = RUN / "policy" / f"state-{k:04d}.npz"
        state = np.load(st_p)["state"] if st_p.exists() else np.load(RUN / "coverage.npz")["state"]
        # D: display voxels created by this fixation
        lo, hi = np.searchsorted(self.vfirst, [k, k + 1])
        changed = zsplat(self.d_img, self.d_z, self.vx[lo:hi], self.vy[lo:hi], self.vz[lo:hi],
                         self.D["vox_panel"]["rgb"][lo:hi])
        # A: trajectory so far (segment into this fixation)
        al = np.asarray(self.traj.getchannel("A"), np.float32)
        fade = al > TRAIL_FLOOR
        al[fade] = np.maximum(TRAIL_FLOOR, al[fade] * TRAIL_DECAY)
        self.traj.putalpha(Image.fromarray(np.rint(al).astype(np.uint8)))
        if k > 1:
            glob = e["kind"] == "global"
            ld = ImageDraw.Draw(self.traj)
            for r in eq_runs(arc(self.dirs[k - 2], self.dirs[k - 1]), EQ_W, EQ_H):
                if glob:
                    dashed_polyline(ld, r, C_GLOBAL + (230,), width=2, dash=9.0, gap=7.0)
                else:
                    ld.line(r, fill=C_LOCAL + (230,), width=2)
        with np.load(CACHE / "eyes" / f"fix-{k:04d}.npz") as z:
            left, right = z["left"], z["right"]
        target = np.median(xyz, axis=0) if len(xyz) else self.dirs[k - 1] * 2.0
        return {"e": e, "state": state, "changed": changed, "left": left, "right": right,
                "depth": depth_patch(cal, xyz), "valid": int(len(xyz)), "target3d": target}

    # ---------------- composition
    def frame(self, k: int, s: dict) -> Image.Image:
        e, nxt = s["e"], s["e"]["next"]
        img = self.static.copy()
        d = ImageDraw.Draw(img)
        glob_next = bool(nxt) and nxt["kind"] == "global"
        self._strip(img, d, k, e, nxt)
        # ---- A
        a = self.a_bg.copy().convert("RGBA")
        a.alpha_composite(self.traj)
        a = a.convert("RGB")
        self._gaze_overlays(a, k, nxt)
        img.paste(a, (EQ_POS[0], STRIP_H + EQ_POS[1]))
        # ---- C
        st = s["state"][self.c_r][:, self.c_c]
        c = np.empty((EQ_H, EQ_W, 3), np.uint8)
        c[st == X.UNSEEN] = C_UNSEEN
        c[st == X.SEEN] = C_SEEN
        c[st == X.DEPTH] = C_DEPTH
        own = (st == X.DEPTH) & self.c_have
        c[own] = np.rint((1 - C_TINT) * self.c_rgb[own] + C_TINT * np.array(C_DEPTH)).astype(np.uint8)
        c[(st == X.UNSEEN) & self.c_dots] = S.STIPPLE
        ci = Image.fromarray(c)
        self._gaze_overlays(ci, k, nxt)
        img.paste(ci, (EQ_POS[0], STRIP_H + PH + EQ_POS[1]))
        # ---- B
        self._eyes(img, d, s)
        # ---- D
        dimg = self.d_img.copy()
        if len(s["changed"]):
            fl = dimg.reshape(-1, 3)
            fl[s["changed"]] = np.rint(0.45 * fl[s["changed"]] + 0.55 * np.array(S.OI_YELLOW)).astype(np.uint8)
        di = Image.fromarray(dimg)
        dd = ImageDraw.Draw(di)
        hx, hy, _ = self.cam.project(np.zeros(3))
        tx, ty, _ = self.cam.project(s["target3d"])
        col = C_GLOBAL if e["kind"] == "global" else (C_LOCAL if e["kind"] == "local" else S.INK)
        dd.line([float(hx), float(hy), float(tx), float(ty)], fill=S.WHITE, width=6)
        dd.line([float(hx), float(hy), float(tx), float(ty)], fill=col, width=3)
        S.crosshair(dd, float(hx), float(hy), r=11)
        dd.ellipse([float(tx) - 5, float(ty) - 5, float(tx) + 5, float(ty) + 5], fill=col, outline=S.WHITE, width=2)
        S.text(dd, (8, EQ_H - 24), "1.5 cm display voxels of the frozen map, coloured by own RGB; ceiling removed; "
                                   "yellow = added by this fixation", size=13, fill=S.INK2, plate=(255, 255, 255))
        img.paste(di, (PW + EQ_POS[0], STRIP_H + PH + EQ_POS[1]))
        return img

    def _gaze_overlays(self, im: Image.Image, k: int, nxt: dict | None) -> None:
        d = ImageDraw.Draw(im)
        e = self.T[k - 1]
        draw_runs(d, eq_runs(footprint_dirs(e["yaw_deg"], e["pitch_deg"]), EQ_W, EQ_H), S.INK, 2)
        x, y = eq_xy(e["yaw_deg"], e["pitch_deg"], EQ_W, EQ_H)
        S.crosshair(d, float(x), float(y), r=10, width=2)
        if nxt and nxt["kind"] in ("local", "global"):
            g = nxt["kind"] == "global"
            nd = X.direction(nxt["yaw_deg"], nxt["pitch_deg"])
            draw_runs(d, eq_runs(arc(self.dirs[k - 1], nd), EQ_W, EQ_H), C_GLOBAL if g else C_LOCAL, 4 if g else 3,
                      dashed=g)
            nx, ny = eq_xy(nxt["yaw_deg"], nxt["pitch_deg"], EQ_W, EQ_H)
            S.ring(d, float(nx), float(ny), r=8, color=C_GLOBAL if g else C_LOCAL, width=3)

    def _eyes(self, img: Image.Image, d, s: dict) -> None:
        x0, y0 = PW + 32, STRIP_H + 50
        sz = 330
        for i, (lab, arr) in enumerate((("LEFT EYE", s["left"]), ("RIGHT EYE", s["right"]))):
            x = x0 + i * (sz + 14)
            img.paste(Image.fromarray(arr).resize((sz, sz), Image.BICUBIC), (x, y0))
            d.rectangle([x - 1, y0 - 1, x + sz, y0 + sz], outline=S.INK2, width=1)
            S.text(d, (x + 8, y0 + 8), lab, size=15, bold=True, plate=(255, 255, 255))
        xd = x0 + 2 * (sz + 14) + 6
        dsz = 196
        img.paste(Image.fromarray(s["depth"]).resize((dsz, dsz), Image.NEAREST), (xd, y0))
        d.rectangle([xd - 1, y0 - 1, xd + dsz, y0 + dsz], outline=S.INK2, width=1)
        S.text(d, (xd, y0 + dsz + 6), "DERIVED METRIC DEPTH", size=13, bold=True, outline=None)
        S.text(d, (xd, y0 + dsz + 24), "left-eye range, saved points", size=12, fill=S.INK2, outline=None)
        cb_y = y0 + dsz + 48
        bar = depth_colors(np.linspace(DMIN, DMAX, dsz))[None].repeat(12, 0)
        img.paste(Image.fromarray(bar), (xd, cb_y))
        for v in (1, 2, 3, 4, 5):
            xx = xd + (v - DMIN) / (DMAX - DMIN) * dsz
            d.line([xx, cb_y + 12, xx, cb_y + 16], fill=S.INK2)
            S.text(d, (xx, cb_y + 17), f"{v} m", size=12, fill=S.INK2, outline=None, anchor="ma")
        S.text(d, (xd, cb_y + 36), "grey: no correspondence", size=12, fill=S.MUTED, outline=None)
        yb = y0 + sz + 12
        b = tag(img, x0, yb, "PERFECT / ORACLE CORRESPONDENCE", "oracle", size=13)
        tag(img, b[2] + 10, yb, "DERIVED METRIC DEPTH", "derived", size=13)
        S.text(d, (x0, yb + 34), f"{s['valid']:,d} metric points from 65,536 foveal pixels", size=16, bold=True,
               outline=None)
        S.text(d, (x0, yb + 58), "eye images: post-hoc display re-render of this fixation's saved calibration "
                                 "(presentation only)", size=13, fill=S.MUTED, outline=None)

    def _strip(self, img, d, k: int, e: dict, nxt: dict | None) -> None:
        glob = bool(nxt) and nxt["kind"] == "global"
        if glob:
            d.rectangle([0, 0, W, STRIP_H - 1], fill=(253, 233, 220))
        S.text(d, (32, 10), "FIXATION", size=14, fill=S.INK2, outline=None)
        S.text(d, (32, 26), f"{k} / {self.N}", size=30, bold=True, outline=None)
        if nxt is None:
            tag(img, 230, 20, "99 % SEEN · STOP", "stop", size=18)
        elif glob:
            tag(img, 230, 20, "NEXT: GLOBAL SACCADE → largest unseen region", "global", size=18)
        else:
            tag(img, 230, 20, f"NEXT: LOCAL SACCADE ({nxt.get('dir', '')})", "local", size=18)
        x = 760
        for lab, val in (("SEEN", f"{100 * e['seen_fraction']:.1f} %"), ("DEPTH", f"{100 * e['depth_fraction']:.1f} %"),
                         ("SURFELS", f"{e['fusion']['map_after']:,d}")):
            S.text(d, (x, 10), lab, size=14, fill=S.INK2, outline=None)
            S.text(d, (x, 26), val, size=28, bold=True, outline=None)
            x += 200 if lab != "SURFELS" else 0
        S.text(d, (W - 32, 14), "FIXATE → RECONSTRUCT → SACCADE", size=18, bold=True, fill=S.INK2, outline=None,
               anchor="ra")
        tag(img, W - 32, 40, "CONTROLLER-TIME VALUES", "controller", size=12, right=True)
        d.rectangle([0, STRIP_H - 6, W, STRIP_H - 1], fill=(228, 226, 220))
        d.rectangle([0, STRIP_H - 6, int(W * e["seen_fraction"]), STRIP_H - 1], fill=C_SEEN)
        d.rectangle([0, STRIP_H - 6, int(W * e["depth_fraction"]), STRIP_H - 1], fill=C_DEPTH)


def frames_for(e: dict) -> int:
    nxt = e["next"]
    return 3 if (nxt and nxt["kind"] == "global") else 2


# ================================================================== headline numbers (from the frozen records only)
def headline(traj: dict, ev: dict) -> dict:
    p, q = ev["primary_all_geometry"], ev["secondary_authored_index_gt_0"]
    return {"fixations": str(traj["fixations"]), "local": str(traj["local_saccades"]),
            "global": str(traj["global_saccades"]), "seen": f"{100 * traj['final_seen_fraction']:.2f} %",
            "depth": f"{100 * traj['final_depth_fraction']:.2f} %",
            "coverage_sr": f"{100 * p['solid_angle_coverage']:.2f} %", "coverage_cells": f"{100 * p['cell_coverage']:.2f} %",
            "covered_cells": f"{p['covered_cells']:,d} / {p['reference_cells']:,d}",
            "authored_sr": f"{100 * q['solid_angle_coverage']:.2f} %", "surfels": f"{traj['final_surfels']:,d}",
            "nn_median_mm": f"{ev['covered_cells_nn_distance_mm']['median']:.2f} mm"}


# ================================================================== intro, freeze, orbit
def intro_card() -> Image.Image:
    img = Image.new("RGB", (W, H), S.SURFACE)
    d = ImageDraw.Draw(img)
    S.text(d, (W / 2, 150), "ACTIVE FOVEAL 3-D VISION", size=78, bold=True, outline=None, anchor="ma")
    S.text(d, (W / 2, 262), "FIXATE  →  RECONSTRUCT  →  SACCADE", size=46, bold=True, fill=S.OI_BLUE, outline=None,
           anchor="ma")
    S.text(d, (W / 2, 338), "360° Classroom reconstruction from a fixed head", size=32, fill=S.INK2, outline=None,
           anchor="ma")
    S.text(d, (W / 2, 410), "A binocular observer with a 12° fovea fixates, reconstructs what it fixates in metric 3-D,",
           size=25, outline=None, anchor="ma")
    S.text(d, (W / 2, 446), "and chooses its next saccade from what it has not yet seen.", size=25, outline=None,
           anchor="ma")
    boxes = [("A", "the 360° scene and the gaze", "Blender reference image, for the viewer only", "reference"),
             ("B", "what the two eyes see now", "and the metric depth they yield", "oracle"),
             ("C", "everything the observer has seen", "UNSEEN  →  SEEN  →  DEPTH", "controller"),
             ("D", "its growing 3-D memory", "one persistent map in the head frame", "derived")]
    bw, bh, gx, gy = 560, 150, 20, 18
    x0, y0 = (W - 2 * bw - gx) / 2, 520
    for i, (letter, l1, l2, kind) in enumerate(boxes):
        x, y = x0 + (i % 2) * (bw + gx), y0 + (i // 2) * (bh + gy)
        d.rounded_rectangle([x, y, x + bw, y + bh], radius=10, fill=S.WHITE, outline=S.FAINT, width=2)
        S.text(d, (x + 24, y + 22), letter, size=44, bold=True, fill=S.INK2, outline=None)
        S.text(d, (x + 84, y + 30), l1, size=24, bold=True, outline=None)
        S.text(d, (x + 84, y + 66), l2, size=19, fill=S.INK2, outline=None)
        tag(img, x + 84, y + 102, {"reference": "REFERENCE / PRESENTATION", "oracle": "ORACLE CORRESPONDENCE",
                                   "controller": "CONTROLLER-TIME", "derived": "DERIVED"}[kind], kind, size=13)
    d.line([x0, 880, x0 + 70, 880], fill=C_LOCAL, width=4)
    S.text(d, (x0 + 84, 866), "local saccade: crawl to a neighbouring view", size=21, outline=None)
    dashed_polyline(d, [(x0 + 600, 880), (x0 + 670, 880)], C_GLOBAL, width=4)
    S.text(d, (x0 + 684, 866), "global saccade: jump to the largest unseen region", size=21, outline=None)
    S.text(d, (W / 2, 990), "PERFECT / ORACLE correspondence  ·  fixed-head synthetic proof of concept (Blender Classroom)",
           size=20, fill=S.MUTED, outline=None, anchor="ma")
    return img


def freeze_overlay(frame: Image.Image, hl: dict) -> Image.Image:
    im = frame.copy()
    d = ImageDraw.Draw(im)
    bw, bh = 1100, 230
    x0, y0 = (W - bw) / 2, (H - bh) / 2
    d.rounded_rectangle([x0, y0, x0 + bw, y0 + bh], radius=14, fill=S.WHITE, outline=S.INK, width=3)
    S.text(d, (W / 2, y0 + 26), f"EXPLORATION COMPLETE  ·  FIXATION {hl['fixations']}", size=32, bold=True,
           outline=None, anchor="ma")
    S.text(d, (W / 2, y0 + 82), f"{hl['seen']} SEEN   ·   {hl['depth']} DEPTH", size=56, bold=True, fill=C_DEPTH,
           outline=None, anchor="ma")
    S.text(d, (W / 2, y0 + 168), "stop rule: SEEN ≥ 99 % of the sphere (controller-time)", size=21, fill=S.INK2,
           outline=None, anchor="ma")
    return im


def orbit_cameras(D: dict, n: int, w: int, h: int) -> list[Camera]:
    vo = D["vox_orbit"]["xyz"]
    az = [24.0 + 110.0 * (0.5 - 0.5 * math.cos(math.pi * i / max(1, n - 1))) for i in range(n)]
    fs = [Camera.fitted(vo, w, h, a, 48.0, 15.0, margin=0.05, target=D["target"]).f for a in az[:: max(1, n // 12)]]
    f = 0.95 * min(fs)
    return [Camera(D["target"], a, 48.0, 15.0, f, w / 2, h / 2) for a in az]


def orbit_frame(D: dict, cam: Camera, hl: dict, w: int = W, h: int = H - 120) -> Image.Image:
    vo = D["vox_orbit"]
    img = Image.new("RGB", (W, H), S.SURFACE)
    view = Image.fromarray(render_points(vo["xyz"], vo["rgb"], cam, w, h))
    dv = ImageDraw.Draw(view)
    hx, hy, _ = cam.project(np.zeros(3))
    S.crosshair(dv, float(hx), float(hy), r=16)
    S.text(dv, (float(hx) + 20, float(hy) + 8), "head (fixed)", size=18, bold=True)
    img.paste(view, (0, 120))
    d = ImageDraw.Draw(img)
    S.text(d, (40, 22), "PERSISTENT 3-D RECONSTRUCTION", size=38, bold=True, outline=None)
    S.text(d, (40, 72), f"{hl['surfels']} surfels from {hl['fixations']} fixations  ·  one map in the fixed head frame",
           size=22, fill=S.INK2, outline=None)
    tag(img, W - 40, 26, "DERIVED · DISPLAY DOWNSAMPLE", "derived", size=16, right=True)
    S.text(d, (W - 40, 70), "1 cm display voxels of the frozen map, own RGB; ceiling removed", size=17, fill=S.INK2,
           outline=None, anchor="ra")
    return img


# ================================================================== stills
def full_map_view(D: dict, w: int, h: int, azim=24.0, elev=52.0) -> tuple[Image.Image, Camera]:
    m, keep = D["map"], D["keep"]
    xyz = m["xyz_h"][keep]
    cam = Camera.fitted(D["vox_panel"]["xyz"], w, h, azim, elev, 14.0, margin=0.04, target=D["target"])
    return Image.fromarray(render_points(xyz, D["rgb8"][keep], cam, w, h)), cam


def paste_framed(img, arr_or_im, box, outline=S.INK2):
    x0, y0, x1, y1 = box
    im = arr_or_im if isinstance(arr_or_im, Image.Image) else Image.fromarray(arr_or_im)
    img.paste(im.resize((x1 - x0, y1 - y0), Image.LANCZOS), (x0, y0))
    ImageDraw.Draw(img).rectangle([x0 - 1, y0 - 1, x1, y1], outline=outline, width=1)


def depth_bar(img, x, y, w, label=True):
    d = ImageDraw.Draw(img)
    img.paste(Image.fromarray(depth_colors(np.linspace(DMIN, DMAX, w))[None].repeat(14, 0)), (x, y))
    for v in (1, 2, 3, 4, 5):
        xx = x + (v - DMIN) / (DMAX - DMIN) * w
        d.line([xx, y + 14, xx, y + 18], fill=S.INK2)
        S.text(d, (xx, y + 19), f"{v} m", size=14, fill=S.INK2, outline=None, anchor="ma")
    if label:
        S.text(d, (x + w + 14, y - 2), "depth = range from the head", size=15, fill=S.INK2, outline=None)


def final_board(D: dict, Rf: dict, hl: dict) -> Image.Image:
    img = Image.new("RGB", (W, H), S.SURFACE)
    d = ImageDraw.Draw(img)
    S.text(d, (40, 22), "RESULT  ·  ONE PERSISTENT 3-D MAP FROM 542 FIXATIONS", size=34, bold=True, outline=None)
    S.text(d, (40, 66), "fixed head  ·  PERFECT / ORACLE correspondence  ·  Blender Classroom  ·  frozen run, "
                        "evaluated only after the explorer stopped", size=18, fill=S.INK2, outline=None)
    tiles = [(hl["fixations"], f"fixations ({hl['local']} local · {hl['global']} global saccades)"),
             (hl["seen"], "of the 360° field observed"), (hl["depth"], "with reconstructed depth"),
             (hl["coverage_sr"], "of first-hit scene solid angle within 12 mm"),
             (hl["surfels"], "surfels in the final map")]
    tw = (W - 80 - 4 * 16) / 5
    for i, (big, cap) in enumerate(tiles):
        x = 40 + i * (tw + 16)
        d.rounded_rectangle([x, 98, x + tw, 208], radius=10, fill=S.WHITE, outline=S.FAINT, width=2)
        S.text(d, (x + 18, 106), big, size=40, bold=True, fill=C_DEPTH if i else S.INK, outline=None)
        S.text(d, (x + 18, 160), cap, size=15, fill=S.INK2, outline=None)
        if big == hl["coverage_sr"]:
            tag(img, x + 18, 182, "REFERENCE / EVALUATION (post-hoc)", "reference", size=10)
    # panoramas: ACTIVE (derived) vs REFERENCE
    pw_, ph_, gap, x0 = 370, 185, 12, 40
    rows = [(222, "ACTIVE RECONSTRUCTION", "projected from the final map (nearest range per pixel)", "derived",
             "DERIVED", D["pano"]),
            (474, "BLENDER REFERENCE", "Breadth-1, 0.5° first hit from the head", "reference",
             "REFERENCE / EVALUATION · NOT AVAILABLE DURING CONTROL", Rf)]
    for y, head, sub, kind, label, src in rows:
        S.text(d, (x0, y), head, size=20, bold=True, outline=None)
        S.text(d, (x0 + d.textlength(head, font=S.font(20, True)) + 14, y + 3), sub, size=15, fill=S.INK2,
               outline=None)
        tag(img, x0 + 3 * pw_ + 2 * gap, y - 2, label, kind, size=12, right=True)
        for j, key in enumerate(("rgb", "depth", "instance")):
            bx = x0 + j * (pw_ + gap)
            paste_framed(img, src[key], (bx, y + 30, bx + pw_, y + 30 + ph_))
            S.text(d, (bx + 6, y + 36), key.upper(), size=13, bold=True, plate=(255, 255, 255))
        tag(img, x0 + 2 * (pw_ + gap), y + 30 + ph_ + 4, "ORACLE SEGMENTATION · VISUALIZATION ONLY", "oracle", size=11)
    depth_bar(img, x0, 728, 2 * pw_ + gap)
    S.text(d, (x0 + 2 * pw_ + gap + 14, 750), "stippled grey: nothing reconstructed / no first hit (windows)", size=14,
           fill=S.MUTED, outline=None)
    # coverage map (REFERENCE / EVALUATION)
    y = 790
    S.text(d, (x0, y), "POST-HOC EVALUATION", size=20, bold=True, outline=None)
    tag(img, x0 + 3 * pw_ + 2 * gap, y - 2, "REFERENCE / EVALUATION · NOT AVAILABLE DURING CONTROL", "reference", size=12,
        right=True)
    paste_framed(img, Rf["coverage"], (x0, y + 32, x0 + 500, y + 282))
    tx = x0 + 530
    lines = [("Breadth-1 first-hit cells within 12 mm of the map", True),
             (f"all geometry:  {hl['covered_cells']} cells = {hl['coverage_cells']}", False),
             (f"solid angle:  {hl['coverage_sr']}", False),
             (f"authored objects (Object Index > 0):  {hl['authored_sr']} solid angle", False),
             (f"median distance, covered cells:  {hl['nn_median_mm']}", False)]
    for i, (s, b) in enumerate(lines):
        S.text(d, (tx, y + 40 + 30 * i), s, size=17, bold=b, fill=S.INK if b else S.INK2, outline=None)
    for i, (lab, col) in enumerate((("covered within 12 mm", S.CORE_GREEN), ("not covered", (222, 220, 214)),
                                    ("no first hit", S.WHITE))):
        yy = y + 205 + 26 * (i // 2)
        xx = tx + (i % 2) * 260
        d.rectangle([xx, yy, xx + 20, yy + 16], fill=col, outline=S.FAINT)
        S.text(d, (xx + 28, yy - 2), lab, size=15, outline=None)
    # final 3-D (the full frozen map below the ceiling cut)
    rx = 1240
    S.text(d, (rx, 222), "FINAL 3-D RECONSTRUCTION", size=20, bold=True, outline=None)
    tag(img, W - 40, 220, "DERIVED · FULL MAP", "derived", size=12, right=True)
    view, cam = full_map_view(D, W - 40 - rx, 760)
    dv = ImageDraw.Draw(view)
    hx, hy, _ = cam.project(np.zeros(3))
    S.crosshair(dv, float(hx), float(hy), r=14)
    S.text(dv, (float(hx) + 18, float(hy) + 6), "head", size=16, bold=True)
    paste_framed(img, view, (rx, 252, W - 40, 1012))
    n_full = int(D["keep"].sum())
    S.text(d, (rx, 1020), f"all {n_full:,d} surfels below the ceiling cut, own RGB; elevated view from behind the head",
           size=14, fill=S.INK2, outline=None)
    return img


def state_image(state: np.ndarray, w: int, h: int) -> np.ndarray:
    r, c = (np.arange(h) * X.H) // h, (np.arange(w) * X.W) // w
    st = state[r][:, c]
    out = np.empty((h, w, 3), np.uint8)
    out[st == X.UNSEEN], out[st == X.SEEN], out[st == X.DEPTH] = C_UNSEEN, C_SEEN, C_DEPTH
    out[(st == X.UNSEEN) & stipple_mask(h, w, 6)] = S.STIPPLE
    return out


def poster(D: dict, T: list[dict], hl: dict, fix_k: int) -> Image.Image:
    PWp, PHp = 2560, 1440
    img = Image.new("RGB", (PWp, PHp), S.SURFACE)
    d = ImageDraw.Draw(img)
    S.text(d, (80, 48), "ACTIVE FOVEAL 3-D VISION", size=86, bold=True, outline=None)
    S.text(d, (82, 156), "FIXATE  →  RECONSTRUCT  →  SACCADE", size=46, bold=True, fill=S.OI_BLUE, outline=None)
    S.text(d, (PWp - 80, 72), "360° Classroom reconstruction from a fixed head", size=34, fill=S.INK2, outline=None,
           anchor="ra")
    S.text(d, (PWp - 80, 124), "PERFECT / ORACLE correspondence · fixed-head synthetic proof of concept", size=22,
           fill=S.MUTED, outline=None, anchor="ra")
    y1 = 262
    # ---- 1-2: one fixation (x 80 .. 820)
    S.text(d, (80, y1), "1 · FIXATE    2 · RECONSTRUCT", size=30, bold=True, outline=None)
    with np.load(CACHE / "eyes" / f"fix-{fix_k:04d}.npz") as z:
        left, right = z["left"], z["right"]
    with np.load(RUN / f"fixations/fix-{fix_k:04d}/points.npz") as z:
        xyz = z["xyz_h"].astype(np.float64)
    cal = read_json(RUN / f"fixations/fix-{fix_k:04d}/calibration.json")
    es = 360
    for i, (lab, arr) in enumerate((("LEFT EYE", left), ("RIGHT EYE", right))):
        x = 80 + i * (es + 20)
        paste_framed(img, arr, (x, y1 + 56, x + es, y1 + 56 + es))
        S.text(d, (x + 10, y1 + 66), lab, size=18, bold=True, plate=(255, 255, 255))
    dy = y1 + 56 + es + 22
    ds = 220
    paste_framed(img, depth_patch(cal, xyz), (80, dy, 80 + ds, dy + ds))
    tx = 80 + ds + 24
    S.text(d, (tx, dy), f"fixation #{fix_k}", size=22, bold=True, outline=None)
    S.text(d, (tx, dy + 32), f"{len(xyz):,d} metric points from one", size=19, fill=S.INK2, outline=None)
    S.text(d, (tx, dy + 58), "binocular look (12° fovea)", size=19, fill=S.INK2, outline=None)
    depth_bar(img, tx, dy + 96, 300, label=False)
    tag(img, tx, dy + 142, "PERFECT / ORACLE CORRESPONDENCE", "oracle", size=13)
    tag(img, tx, dy + 178, "DERIVED METRIC DEPTH", "derived", size=13)
    # ---- 3: exploration (x 880 .. 1700)
    cx0, cw = 880, 820
    S.text(d, (cx0, y1), "3 · SACCADE", size=30, bold=True, outline=None)
    S.text(d, (cx0 + 220, y1 + 6), "the observer's 360° state", size=24, fill=S.INK2, outline=None)
    tag(img, cx0 + cw, y1 + 4, "CONTROLLER-TIME", "controller", size=14, right=True)
    sw, sh = 400, 200
    for i, k in enumerate((50, 200, 450, int(hl["fixations"]))):
        st_p = RUN / "policy" / f"state-{k:04d}.npz"
        state = np.load(st_p)["state"] if st_p.exists() else np.load(RUN / "coverage.npz")["state"]
        x, y = cx0 + (i % 2) * (sw + 20), y1 + 56 + (i // 2) * (sh + 56)
        im = Image.fromarray(state_image(state, sw, sh))
        if i == 3:
            dd = ImageDraw.Draw(im)
            dirs = X.direction(np.array([e["yaw_deg"] for e in T]), np.array([e["pitch_deg"] for e in T]))
            for j in range(1, len(T)):
                g = T[j]["kind"] == "global"
                for r in eq_runs(arc(dirs[j - 1], dirs[j]), sw, sh):
                    if g:
                        dashed_polyline(dd, r, C_GLOBAL, width=1, dash=5.0, gap=4.0)
                    else:
                        dd.line(r, fill=(0, 60, 110), width=1)
        paste_framed(img, im, (x, y, x + sw, y + sh))
        S.text(d, (x, y + sh + 8), f"after fixation {k}:  {100 * T[k - 1]['seen_fraction']:.1f} % seen", size=19,
               bold=True, outline=None)
    ly = y1 + 56 + 2 * (sh + 56) + 4
    lx = cx0
    for lab, col in (("UNSEEN", C_UNSEEN), ("SEEN", C_SEEN), ("DEPTH", C_DEPTH)):
        d.rectangle([lx, ly, lx + 24, ly + 18], fill=col, outline=S.FAINT)
        S.text(d, (lx + 32, ly - 2), lab, size=18, outline=None)
        lx += 130
    d.line([lx + 10, ly + 9, lx + 56, ly + 9], fill=C_LOCAL, width=3)
    S.text(d, (lx + 64, ly - 2), f"{hl['local']} local", size=18, outline=None)
    dashed_polyline(d, [(lx + 170, ly + 9), (lx + 216, ly + 9)], C_GLOBAL, width=3, dash=8.0, gap=6.0)
    S.text(d, (lx + 224, ly - 2), f"{hl['global']} global", size=18, outline=None)
    # ---- 3-D (x 1760 .. 2480)
    rx = 1760
    S.text(d, (rx, y1), "PERSISTENT 3-D MEMORY", size=30, bold=True, outline=None)
    tag(img, PWp - 80, y1 + 4, "DERIVED · FULL MAP", "derived", size=14, right=True)
    view, cam = full_map_view(D, PWp - 80 - rx, 580, azim=45.0, elev=40.0)
    dv = ImageDraw.Draw(view)
    hx, hy, _ = cam.project(np.zeros(3))
    S.crosshair(dv, float(hx), float(hy), r=14)
    S.text(dv, (float(hx) + 18, float(hy) + 6), "head", size=18, bold=True)
    paste_framed(img, view, (rx, y1 + 56, PWp - 80, y1 + 636))
    S.text(d, (rx, y1 + 646), f"{hl['surfels']} surfels in one map (ceiling removed for display)", size=18,
           fill=S.INK2, outline=None)
    # ---- RGB-D panorama (y 960 ..)
    y2 = 1000
    S.text(d, (80, y2 - 52), "RECONSTRUCTED RGB-D PANORAMA", size=30, bold=True, outline=None)
    hx_ = 80 + d.textlength("RECONSTRUCTED RGB-D PANORAMA", font=S.font(30, True)) + 18
    S.text(d, (hx_, y2 - 46), "projected from the persistent map, not the Blender reference", size=21, fill=S.INK2,
           outline=None)
    tag(img, 1700, y2 - 50, "DERIVED", "derived", size=14, right=True)
    pw2 = 800
    paste_framed(img, D["pano"]["rgb"], (80, y2, 80 + pw2, y2 + pw2 // 2))
    paste_framed(img, D["pano"]["depth"], (80 + pw2 + 20, y2, 80 + 2 * pw2 + 20, y2 + pw2 // 2))
    # ---- the four headline numbers
    nx = 1760
    for i, (big, cap) in enumerate(((hl["fixations"], "fixations"), (hl["seen"], "of the 360° field observed"),
                                    (hl["depth"], "with reconstructed depth"),
                                    (hl["coverage_sr"], "of first-hit scene solid angle within 12 mm"))):
        y = y2 - 48 + i * 104
        S.text(d, (nx, y), big, size=56, bold=True, fill=C_DEPTH if i else S.INK, outline=None)
        S.text(d, (nx + 6, y + 66), cap, size=20, fill=S.INK2, outline=None)
    tag(img, PWp - 80, y2 - 48 + 3 * 104 + 18, "REFERENCE / EVALUATION, post-hoc", "reference", size=13, right=True)
    S.text(d, (80, PHp - 30), "Blender Classroom · 64 spp · 542 fixations · prototype/greedy-foveal-explorer-v0 "
                              "(run greedy-foveal-explorer-v0-grow600)", size=15, fill=S.MUTED, outline=None)
    return img


# ================================================================== build
POSTER_FIX = 179                 # chosen for legibility (layered chairs / desks); presentation only


def build(a) -> None:
    fz = verify_run()
    traj = read_json(RUN / "trajectory.json")
    T = traj["trajectory"]
    ev = read_json(RUN / "evaluation.json")
    if len(list((CACHE / "eyes").glob("fix-*.npz"))) != len(T):
        raise SystemExit(f"{PREFIX} REFUSED run `rerender` first")
    OUT.mkdir(parents=True, exist_ok=True)
    hl = headline(traj, ev)
    t0 = time.perf_counter()
    AUDIT.stage = "derived"
    D = derived_assets(T)
    AUDIT.stage = "reference"
    Rf = reference_assets(ev)
    AUDIT.stage = "compose"
    ref_rgb = np.asarray(Image.open(CACHE / REF_RGB_REL).convert("RGB"))
    final = final_board(D, Rf, hl)
    final.save(OUT / "demo-final.png", optimize=True)
    poster(D, T, hl, POSTER_FIX).save(OUT / "demo-poster.png", optimize=True)
    print(f"{PREFIX} stills written ({time.perf_counter() - t0:.0f} s)", flush=True)
    meta = (f"fixations={hl['fixations']}; seen={hl['seen']}; depth={hl['depth']}; "
            f"coverage_solid_angle={hl['coverage_sr']}; coverage_cells={hl['coverage_cells']}; surfels={hl['surfels']}; "
            f"run=greedy-foveal-explorer-v0-grow600; run_freeze_sha256={sha256(RUN / 'freeze.json')}")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
           "-movflags", "+faststart", "-metadata", "title=Active foveal 3-D vision: FIXATE -> RECONSTRUCT -> SACCADE",
           "-metadata", f"comment={meta}", str(OUT / "demo.mp4")]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    schedule: list[list] = []

    def put(im: Image.Image, seg: str, fix: int | None = None, n: int = 1) -> None:
        b = np.asarray(im.convert("RGB"), np.uint8).tobytes()
        for _ in range(n):
            p.stdin.write(b)
            schedule.append([seg, fix])

    intro = intro_card()
    blank = Image.new("RGB", (W, H), S.SURFACE)
    for i in range(12):
        put(Image.blend(blank, intro, (i + 1) / 12), "intro")
    put(intro, "intro", n=108)
    rp = Replay(T, D, ref_rgb)
    last = None
    for e in T:
        k = e["n"]
        s = rp.advance(k)
        last = rp.frame(k, s)
        put(last, "replay", k, frames_for(e))
        if k % 50 == 0:
            print(f"{PREFIX} replay {k}/{len(T)} ({time.perf_counter() - t0:.0f} s)", flush=True)
    put(freeze_overlay(last, hl), "freeze", n=60)
    cams = orbit_cameras(D, 150, W, H - 120)
    ob = None
    for cam in cams:
        ob = orbit_frame(D, cam, hl)
        put(ob, "orbit")
    for i in range(15):
        put(Image.blend(ob, final, (i + 1) / 15), "final")
    put(final, "final", n=225)
    p.stdin.close()
    rc = p.wait()
    if rc != 0:
        raise SystemExit(f"{PREFIX} STOP ffmpeg exited {rc}")
    AUDIT.stage = None
    opens = {k: sorted(v) for k, v in AUDIT.opens.items()}
    replay = [f for seg, f in schedule if seg == "replay"]
    write_json(OUT / "demo-manifest.json", {
        "schema": "GFE-v0-demo-manifest", "label": "PRESENTATION ONLY (offline replay of a frozen run)",
        "run": str(RUN), "run_freeze_sha256": sha256(RUN / "freeze.json"), "run_code": fz["code"],
        "final_map_sha256_used": D["map_sha256"], "final_map_sha256_frozen": fz["files"]["final-map.npz"],
        "headline": hl, "video": {"path": str(OUT / "demo.mp4"), "frames": len(schedule), "fps": FPS,
                                  "size": [W, H], "seconds": len(schedule) / FPS, "metadata_comment": meta,
                                  "segments": {s: sum(1 for x in schedule if x[0] == s)
                                               for s in ("intro", "replay", "freeze", "orbit", "final")}},
        "replay_fixations": replay, "poster_fixation": POSTER_FIX,
        "panels": {"replay A": {"sources": ["reference rgb (" + REF_RGB_REL + ")", "trajectory.json"],
                                "labels": ["REFERENCE / PRESENTATION · NOT AVAILABLE TO CONTROLLER"]},
                   "replay B": {"sources": ["eye cache (post-hoc display re-render)", "points.npz", "calibration.json"],
                                "labels": ["PERFECT / ORACLE CORRESPONDENCE", "DERIVED METRIC DEPTH"]},
                   "replay C": {"sources": ["policy/state-*.npz", "coverage.npz", "points.npz"],
                                "labels": ["CONTROLLER-TIME"]},
                   "replay D": {"sources": ["final-map.npz (first-fixation provenance)", "points.npz"],
                                "labels": ["DERIVED · DISPLAY DOWNSAMPLE"]},
                   "final ACTIVE row": {"sources": ["final-map.npz"], "labels": ["DERIVED"]},
                   "final REFERENCE row": {"sources": ["Breadth-1 canonical.exr"],
                                           "labels": ["REFERENCE / EVALUATION · NOT AVAILABLE DURING CONTROL"]},
                   "final coverage": {"sources": ["evaluation.npz (Breadth-1 cells)"],
                                      "labels": ["REFERENCE / EVALUATION · NOT AVAILABLE DURING CONTROL"]},
                   "final ACTIVE instance panorama": {"sources": ["final-map.npz oracle id"],
                                                      "labels": ["DERIVED", "ORACLE SEGMENTATION · VISUALIZATION ONLY"]},
                   "final REFERENCE instance panorama": {"sources": ["Breadth-1 Object Index"],
                                                         "labels": ["REFERENCE / EVALUATION · NOT AVAILABLE DURING "
                                                                    "CONTROL", "ORACLE SEGMENTATION · VISUALIZATION ONLY"]},
                   "final headline 98.32 % tile": {"sources": ["evaluation.json (Breadth-1 evaluation)"],
                                                   "labels": ["REFERENCE / EVALUATION"]},
                   "poster headline 98.32 %": {"sources": ["evaluation.json (Breadth-1 evaluation)"],
                                               "labels": ["REFERENCE / EVALUATION, post-hoc"]}},
        "stage_opens": opens, "eyes_manifest_sha256": sha256(CACHE / "eyes-manifest.json"),
        "build_seconds": time.perf_counter() - t0})
    print(f"{PREFIX} wrote {OUT / 'demo.mp4'}: {len(schedule)} frames = {len(schedule) / FPS:.1f} s "
          f"({time.perf_counter() - t0:.0f} s)", flush=True)


# ================================================================== minimal demo checks
def check(a) -> None:
    traj = read_json(RUN / "trajectory.json")
    ev = read_json(RUN / "evaluation.json")
    fz = read_json(RUN / "freeze.json")
    man = read_json(OUT / "demo-manifest.json")
    res = {}
    rf = man["replay_fixations"]
    seq = [rf[0]] + [b for a_, b in zip(rf, rf[1:]) if b != a_]
    res["replay_in_exact_order"] = (seq == [e["n"] for e in traj["trajectory"]] == list(range(1, 543))
                                    and all(b >= a_ for a_, b in zip(rf, rf[1:])))
    probe = json.loads(subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-show_entries",
                                       "stream=width,height,r_frame_rate,nb_read_frames,codec_name:format=duration:"
                                       "format_tags=comment", "-of", "json", str(OUT / "demo.mp4")],
                                      capture_output=True, text=True, check=True).stdout)
    st, fm = probe["streams"][0], probe["format"]
    comment = dict(kv.split("=", 1) for kv in fm["tags"]["comment"].split("; "))
    res["metadata_seen_depth_equal_run"] = (comment["seen"] == f"{100 * traj['final_seen_fraction']:.2f} %"
                                            and comment["depth"] == f"{100 * traj['final_depth_fraction']:.2f} %"
                                            and comment["seen"] == "99.00 %" and comment["depth"] == "98.28 %")
    res["final_map_from_frozen_run"] = (man["final_map_sha256_used"] == fz["files"]["final-map.npz"]
                                        == sha256(RUN / "final-map.npz"))
    op = man["stage_opens"]
    b1 = str(B1_EXR)
    res["no_reference_in_derived_stage"] = not any("breadth-1" in p or "/reference/" in p or "evaluation" in p
                                                   for p in op.get("derived", []))
    res["reference_only_where_labelled"] = (
        any(p == b1 for p in op.get("reference", []))
        and not any("breadth-1" in p for p in op.get("compose", []))
        and [p for p in op.get("compose", []) if "/reference/" in p] == [str(CACHE / REF_RGB_REL)]
        and all(any("REFERENCE" in lab for lab in v["labels"]) for v in man["panels"].values()
                if any("reference" in s.lower() or "breadth-1" in s.lower() for s in v["sources"])))
    hl = headline(traj, ev)
    res["headline_equals_evaluation"] = (man["headline"] == hl and hl["coverage_sr"] == "98.32 %"
                                         and hl["coverage_cells"] == "98.52 %" and hl["surfels"] == "16,517,811"
                                         and hl["fixations"] == "542")
    n = int(st["nb_read_frames"])
    res["mp4_frames_and_size"] = (st["codec_name"] == "h264" and (st["width"], st["height"]) == (W, H)
                                  and st["r_frame_rate"] == f"{FPS}/1" and n == man["video"]["frames"])
    for k, v in res.items():
        print(f"{PREFIX} check {k}: {v}", flush=True)
    print(f"{PREFIX} video {n} frames, {float(fm['duration']):.2f} s, {st['width']}x{st['height']} @ "
          f"{st['r_frame_rate']}", flush=True)
    ok = all(res.values())
    write_json(OUT / "demo-checks.json", {"all_pass": ok, "checks": res, "ffprobe": probe})
    print(f"{PREFIX} CHECKS {'PASS' if ok else 'FAIL'}", flush=True)
    if not ok:
        raise SystemExit(1)


# ================================================================== entry point
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("rerender", "build", "check"))
    a = ap.parse_args()
    {"rerender": rerender, "build": build, "check": check}[a.cmd](a)


if __name__ == "__main__":
    main()
