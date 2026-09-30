#!/usr/bin/env python3
"""Visual Language 1 + the full canonical Classroom demo (generator).

Contract: docs/methodology/visual-language-1-contract.md.

    G=tools/visual_language/generate_visual_language1.py
    .venv/bin/python $G extract   --source RUN01 --replay RUN02 --cache CACHE
    .venv/bin/python $G reference --source RUN01 --cache CACHE --out PACKAGE      (optional; REFERENCE path)
    .venv/bin/python $G render    --source RUN01 --replay RUN02 --cache CACHE --out PACKAGE

``extract`` and ``render`` are the controller-time paths (truth firewall: no evaluation truth,
no reference product, no earlier audit).  ``reference`` is the separate reference path; ``render``
composes its already-written, REFERENCE-tagged products into the intro/outro only through the
separate ``compose-reference`` step, run in its own process after ``render``.
"""
from __future__ import annotations

import argparse
import json
import math
import multiprocessing as mp
import os
from pathlib import Path
import shutil
import subprocess
import sys
import textwrap
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import cv2  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

import style as S  # noqa: E402
import vl1_data as D  # noqa: E402
import vl1_draw as V  # noqa: E402

FPS = 30
HOLD = {"ordinary": 23, "switch": 36}
SRC_LABEL = {"oracle_seed": "seed look", "fsg6f": "FSG6f look", "cyclopean_epistemic": "Cyclopean look"}
CHART_W, CHART_H = 625, 500
INSET_W, INSET_H = 621, 330
UNMEASURED = (238, 237, 233)


# ---------------------------------------------------------------- shared context

class Ctx:
    """Everything a frame needs that is not per-step state (loaded under the firewall)."""

    def __init__(self, source: Path, replay: Path, cache: Path):
        self.src = D.Sources(source, replay)
        self.cache = Path(cache)
        self.steps = json.loads((self.cache / "steps.json").read_text())
        self.events = json.loads((self.cache / "events.json").read_text())
        self.c02_events = self.src.c02_events
        self.actions = self.src.actions
        self.n = len(self.actions)
        self.domain = self.src.domain
        self.chart = V.Chart(-25.0, 25.0, -20.0, 20.0, D.CHART_PPD)
        cam = json.loads((self.cache / "camera.json").read_text())
        self.cam = V.Camera3D(bounds_uv=cam["bounds"])
        self.dlim = tuple(cam["depth_limits"])
        self.bouts = []
        prev = None
        for a in self.actions:
            if a["target_id"] != prev:
                self.bouts.append([a["global_step"], a["global_step"]])
                prev = a["target_id"]
            else:
                self.bouts[-1][1] = a["global_step"]

    def bout_of(self, t):
        for b in self.bouts:
            if b[0] <= t <= b[1]:
                return b
        raise KeyError(t)

    def step_npz(self, t):
        return D.load_npz(self.cache / f"steps/step_{t:03d}.npz")

    def raster(self, t):
        name = "after_-001" if t < 0 else f"after_{t:03d}"
        img = cv2.imread(str(self.cache / f"raster/{name}.png"))[..., ::-1].copy()
        inst = D.load_npz(self.cache / f"raster/{name}.npz")["inst"]
        return img, inst


class Memory:
    """Worker-local causal memory: measurement points by step, and each object's latest active map."""

    def __init__(self, ctx: Ctx):
        self.ctx = ctx
        self.upto = -1
        self.xyz, self.rgb, self.inst, self.yp = [], [], [], []
        self.maps: dict[int, np.ndarray] = {}
        self.map_rgb: dict[int, np.ndarray] = {}

    def advance(self, t):
        """Include steps <= t."""
        src = self.ctx.src
        while self.upto < t:
            s = self.upto + 1
            a = self.ctx.actions[s]
            i, k = int(a["target_id"]), int(a["object_local_step"])
            p = src.patch(i, k)
            L, _R = src.benchmark(i, k)
            m = p["valid"] & (p["instance_id"] > 0)
            xyz = p["xyz_h"][m].astype(np.float32)
            self.xyz.append(xyz); self.rgb.append(L[m]); self.inst.append(p["instance_id"][m])
            y, pp = D.angles(xyz)
            self.yp.append(np.c_[y, pp].astype(np.float32))
            mf = src.map_file(i, k)
            if mf.exists():
                z = D.load_npz(mf)
                self.maps[i] = np.asarray(z["xyz_h"], np.float32)
                self.map_rgb[i] = D.gamma_u8(z["rgb"])
            self.upto = s

    def points(self, window=None):
        if not self.xyz:
            return np.empty((0, 3), np.float32), np.empty((0, 3), np.uint8), np.empty(0, np.int32)
        xyz, rgb, inst, yp = (np.concatenate(v) for v in (self.xyz, self.rgb, self.inst, self.yp))
        if window is not None:
            y0, y1, p0, p1 = window
            k = (yp[:, 0] >= y0 - 0.5) & (yp[:, 0] <= y1 + 0.5) & (yp[:, 1] >= p0 - 0.5) & (yp[:, 1] <= p1 + 0.5)
            return xyz[k], rgb[k], inst[k]
        return xyz, rgb, inst

    def union_maps(self):
        if not self.maps:
            return np.empty((0, 3), np.float32), np.empty(0, np.int32)
        ids = sorted(self.maps)
        return (np.concatenate([self.maps[i] for i in ids]),
                np.concatenate([np.full(len(self.maps[i]), i, np.int32) for i in ids]))


def lighten(img: np.ndarray, a=0.35) -> np.ndarray:
    return (img.astype(np.float32) * (1 - a) + 255 * a).astype(np.uint8)


def fmt(n) -> str:
    return f"{int(n):,}"


def gaze_text(g) -> str:
    return f"[{g[0]:.1f}, {g[1]:.1f}]"


def states_after(ctx: Ctx, t: int) -> dict[int, str]:
    return {int(k): V.tile_state(v) for k, v in ctx.src.c02_actions[t]["service_states_after"].items()}


def states_before(ctx: Ctx, t: int) -> dict[int, str]:
    return {int(k): V.tile_state(v) for k, v in ctx.src.c02_actions[t]["service_states_before"].items()}


def causal_window(ctx: Ctx, t: int, pts_fn, min_w=10.0):
    """A zoom window grown monotonically over the attention bout up to step t (never uses the future)."""
    b0, _b1 = ctx.bout_of(t)
    pts = []
    for s in range(b0, t + 1):
        pts.extend(pts_fn(s))
    return V.fit_window(np.asarray(pts), min_w=min_w, aspect=INSET_W / INSET_H, margin=1.0)


def core_box_points(g, half=6.0):
    return [(g[0] - half, g[1] - half), (g[0] + half, g[1] + half)]


def marks_chart(img: Image.Image, chart: V.Chart, current=None, proposed=None, switch=False, r=15, labels=True):
    d = ImageDraw.Draw(img)
    if current is not None and proposed is not None:
        x0, y0 = chart.pt(current); x1, y1 = chart.pt(proposed)
        L = math.hypot(x1 - x0, y1 - y0)
        if L > 2 * r + 6:
            ux, uy = (x1 - x0) / L, (y1 - y0) / L
            S.arrow(d, x0 + ux * (r + 4), y0 + uy * (r + 4), x1 - ux * (r + 4), y1 - uy * (r + 4), width=3, head=16,
                    double=switch)
    if current is not None:
        x, y = chart.pt(current)
        S.crosshair(d, x, y, r=r, solid=True)
    if proposed is not None:
        x, y = chart.pt(proposed)
        S.crosshair(d, x, y, r=r, solid=False)


# ---------------------------------------------------------------- the four cockpit panels

def panel_scene(ctx: Ctx, mem: Memory, t: int) -> tuple[Image.Image, dict]:
    """1 SCENE / ATTENTION, BEFORE action t."""
    a = ctx.actions[t]
    i = int(a["target_id"])
    prev = ctx.actions[t - 1] if t > 0 else None
    switch = prev is None or int(prev["target_id"]) != i
    cur = tuple(prev["gaze_deg"]) if prev else None
    prop = tuple(a["gaze_deg"])
    img, inst = ctx.raster(t - 1)
    img = lighten(img, 0.30)
    img[inst == 0] = UNMEASURED
    main = Image.fromarray(img)
    V.outline(main, inst == i, S.INK, width=3, halo=S.WHITE)
    d = ImageDraw.Draw(main)
    for b in ctx.actions[:t]:
        x, y = ctx.chart.pt(b["gaze_deg"])
        d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=S.INK2)
    V.grid_lines(main, ctx.chart, labels=True)
    marks_chart(main, ctx.chart, cur, prop, switch)
    if prev is None:
        S.text(ImageDraw.Draw(main), (ctx.chart.pt(prop)[0] + 24, ctx.chart.pt(prop)[1] - 44), "first look", size=S.T_BODY,
               bold=True, plate=S.WHITE)

    def pts_fn(s):
        b = ctx.actions[s]
        out = core_box_points(b["gaze_deg"], 5.0)
        if s > 0:
            out += [tuple(ctx.actions[s - 1]["gaze_deg"])]
        return out
    win = causal_window(ctx, t, pts_fn)
    ch = V.Chart(*win, INSET_W / (win[1] - win[0]))
    xyz, rgb, ins = mem.points(win)
    z = np.full((ch.h, ch.w, 3), S.PANEL, np.uint8)
    rad = 1 if ch.s < 60 else 2
    z = V.splat(ch, xyz, rgb, img=z, radius=rad)
    tz = V.splat(ch, xyz[ins == i], (255, 255, 255), img=np.zeros_like(z), radius=rad)
    inset = Image.fromarray(lighten(z, 0.22))
    V.outline(inset, tz.any(-1), S.INK, width=4, halo=S.WHITE)
    marks_chart(inset, ch, cur if cur and ch.inside(cur, 3) else None, prop, switch, r=20)
    di = ImageDraw.Draw(inset)
    di.rectangle([0, 0, ch.w - 1, ch.h - 1], outline=S.INK, width=2)
    S.text(di, (10, 8), "ZOOM", size=S.T_SMALL, bold=True, plate=S.WHITE)
    # locator on the main chart
    x0, y0 = ctx.chart.pt((win[0], win[3])); x1, y1 = ctx.chart.pt((win[1], win[2]))
    S.dashed_rect(ImageDraw.Draw(main), [x0, y0, x1, y1], S.INK, width=2, dash=6, gap=5)
    content = Image.new("RGB", (V.CONTENT_W, V.CONTENT_H), S.PANEL)
    content.paste(main.crop((0, 0, CHART_W, CHART_H)), (0, 0))
    content.paste(inset.resize((INSET_W, INSET_H)) if inset.size != (INSET_W, INSET_H) else inset, (CHART_W + 10, 0))
    st_before = ctx.src.c02_actions[t]["service_states_before"][str(i)]
    own_before = sum(1 for b in ctx.actions[:t] if b["target_id"] == i)
    if prev is None:
        dec = "first look of the run"
    elif switch:
        dec = f"SWITCH: {prev['target_id']} → {i}"
    else:
        dec = f"retain {i} (same object)"
    why = {"oracle_seed": "seed direction (ORACLE INPUT)", "fsg6f": "FSG6f local proposal",
           "cyclopean_epistemic": "Cyclopean local proposal"}[a["action_source"]]
    V.plate_lines(content, (CHART_W + 16, INSET_H + 10), [
        (f"target {i} {ctx.src.names(i)}", {"bold": True, "size": S.T_HEAD}),
        f"state before: {st_before.replace('/', ' / ')} · own looks {own_before}",
        f"decision: {dec}",
        f"next look from: {why}",
    ], size=S.T_BODY, gap=9)
    meta = {"switch": switch, "current_gaze": cur, "proposed_gaze": prop, "state_before": st_before,
            "own_looks_before": own_before, "inset_window": list(win)}
    return content, meta


def raw_view(ctx: Ctx, t: int, size=320):
    a = ctx.actions[t]
    i, k = int(a["target_id"]), int(a["object_local_step"])
    c, obs = ctx.src.acquisition(i, k)
    raw = D.gamma_u8(obs["rgb_L"])
    im = Image.fromarray(raw).resize((size, size), Image.LANCZOS)
    sc = size / raw.shape[1]
    tgt = cv2.resize((obs["instance_L"] == i).astype(np.uint8), (size, size), interpolation=cv2.INTER_NEAREST)
    V.outline(im, tgt > 0, S.INK, width=2, halo=S.WHITE)
    from fov3d.stereo.core import rectification
    r = rectification(c)
    x, y, w, h = (int(v) for v in r["crop_xywh"])
    xs = np.r_[np.arange(x, x + w), np.full(h, x + w - 1), np.arange(x + w - 1, x - 1, -1), np.full(h, x)]
    ys = np.r_[np.full(w, y), np.arange(y, y + h), np.full(w, y + h - 1), np.arange(y + h - 1, y - 1, -1)]
    mx, my = r["map_Lx"][ys, xs], r["map_Ly"][ys, xs]
    d = ImageDraw.Draw(im)
    pts = [(float(u * sc), float(v * sc)) for u, v in zip(mx[::8], my[::8])]
    d.line(pts + [pts[0]], fill=S.WHITE, width=6)
    d.line(pts + [pts[0]], fill=S.CORE_GREEN, width=3)
    return im, c, obs


def panel_eyes(ctx: Ctx, t: int) -> tuple[Image.Image, dict]:
    """2 THE EYES: the observation produced by action t."""
    a = ctx.actions[t]
    sm = ctx.steps[t]
    i, k = int(a["target_id"]), int(a["object_local_step"])
    z = ctx.step_npz(t)
    L, R = ctx.src.benchmark(i, k)
    patch = ctx.src.patch(i, k)
    sz = 448
    up = lambda m: cv2.resize(m.astype(np.uint8), (sz, sz), interpolation=cv2.INTER_NEAREST) > 0
    Li = np.asarray(Image.fromarray(L).resize((sz, sz), Image.LANCZOS)).astype(np.float32)
    rep, new, tpx = up(z["repeated_px"]), up(z["new_px"]), up(z["target_px"])
    nodepth = up(z["target_px"] & ~patch["valid"])
    Li[rep] = Li[rep] * 0.55 + np.array(S.OI_PURPLE) * 0.45
    Li[new] = Li[new] * 0.15 + np.array(S.OI_GREEN) * 0.85
    left = Image.fromarray(Li.astype(np.uint8))
    S.hatch(left, (0, 0, sz, sz), S.INK, spacing=8, width=2, mask=Image.fromarray((nodepth * 255).astype(np.uint8)))
    cells = []
    cs = 12
    for yy in range(0, sz, cs):
        for xx in range(0, sz, cs):
            if rep[yy:yy + cs, xx:xx + cs].mean() > 0.5:
                cells.append((xx + cs / 2, yy + cs / 2))
    V.lattice_marks(left, cells, "ring", S.OI_PURPLE, r=4, width=2)
    V.outline(left, tpx, S.INK, width=3, halo=S.WHITE)
    raw, c, obs = raw_view(ctx, t)
    from fov3d.experiments.classroom_oracle import matcher
    _rec, _m, st = matcher.compute(c, obs)
    right = Image.fromarray(R).resize((sz, sz), Image.LANCZOS)
    V.outline(right, up(st["ids_right"] == i), S.INK, width=3, halo=S.WHITE)
    content = Image.new("RGB", (V.CONTENT_W, V.CONTENT_H), S.PANEL)
    content.paste(left, (0, 0)); content.paste(right, (sz + 8, 0))
    d = ImageDraw.Draw(content)
    for x, lab in ((0, "LEFT eye · depth-measuring core"), (sz + 8, "RIGHT eye · depth-measuring core")):
        d.text((x + 4, sz + 8), lab, font=S.font(S.T_SMALL, True), fill=S.INK)
    for im_, x in ((left, 0), (right, sz + 8)):
        dd = ImageDraw.Draw(content)
        dd.rectangle([x, 0, x + sz - 1, sz - 1], outline=S.CORE_GREEN, width=4)
    rx = 2 * sz + 24
    content.paste(raw, (rx, 0))
    d.text((rx, 326), "wide view 29° (left eye): visible", font=S.font(S.T_SMALL - 2), fill=S.INK2)
    d.text((rx, 350), "green box: 12° depth core", font=S.font(S.T_SMALL - 2, True), fill=S.CORE_GREEN)
    V.plate_lines(content, (rx, 382), [
        (f"target-valid  {fmt(sm['target_valid_points'])}", {"bold": True}),
        f"all valid     {fmt(sm['all_valid_points'])}",
        f"target, no depth  {fmt(sm['target_pixels_without_depth'])}",
    ], size=S.T_SMALL, gap=6)
    meta = {"target_valid_points": sm["target_valid_points"], "all_valid_points": sm["all_valid_points"],
            "target_pixels_without_depth": sm["target_pixels_without_depth"],
            "observation_files": [f"objects/instance_{i:04d}/benchmark/fix_{k:02d}_L.png",
                                  f"objects/instance_{i:04d}/benchmark/fix_{k:02d}_R.png",
                                  f"objects/instance_{i:04d}/patches/fix_{k:02d}.npz",
                                  f"objects/instance_{i:04d}/acquisitions/fix_{k:02d}/oracle_observation.npz",
                                  f"objects/instance_{i:04d}/acquisitions/fix_{k:02d}/calibration.json"]}
    return content, meta


def probe_lines(pr: dict) -> tuple[list, tuple | None, str]:
    f6, cy = pr["fsg6f"], pr["cyclopean"]
    if not f6["stop"]:
        return ([f"FSG6f: continue · OPEN {f6['frontier_open_count']} · candidates {f6['candidates']}"],
                tuple(f6["next_gaze_deg"]), "fsg6f")
    lines = [f"FSG6f: {f6['reason'].replace('_', ' ')} · OPEN {f6['frontier_open_count']}"]
    if cy is not None:
        lines.append(f"Cyclopean: eligible cells {cy['eligible_cells']}")
        if not cy["stop"]:
            return lines, tuple(cy["next_gaze_deg"]), "cyclopean_epistemic"
    return lines, None, "QUIET"


def unresolved_marks(img: Image.Image, chart: V.Chart, z: dict, r=4, lattice=6):
    d = ImageDraw.Draw(img)
    yp, stt = z["frontier_yaw_pitch"], z["frontier_state"]
    opened = yp[stt == 0] if len(yp) else np.empty((0, 2))
    seen = set()
    for yy, pp in opened:
        x, y = chart.pt((yy, pp))
        key = (int(x // lattice), int(y // lattice))
        if key in seen or not (0 <= x < chart.w and 0 <= y < chart.h):
            continue
        seen.add(key)
        S.ring(d, x, y, r=r, color=S.OI_VERM, width=2)
    el = np.argwhere(z["eligible"])
    for cy_, cx_ in el:
        yaw, pit = -25.0 + cx_ * D.GRID_DEG, -20.0 + cy_ * D.GRID_DEG
        x, y = chart.pt((yaw, pit))
        key = (int(x // lattice), int(y // lattice))
        if key in seen or not (0 <= x < chart.w and 0 <= y < chart.h):
            continue
        seen.add(key)
        S.ring(d, x, y, r=r, color=S.OI_VERM, width=2)
    return int(len(opened)), int(len(el))


def quiet_stamp(img: Image.Image, x, y, size=S.T_HEAD):
    d = ImageDraw.Draw(img)
    s = "QUIET ✓"
    f = S.font(size, True)
    tw = d.textlength(s, font=f)
    box = [x - tw / 2 - 12, y - size / 2 - 8, x + tw / 2 + 12, y + size / 2 + 8]
    d.rectangle(box, fill=S.SLATE, outline=S.INK, width=3)
    d.text((box[0] + 12, box[1] + 6), s, font=f, fill=S.INK)


def panel_epistemic(ctx: Ctx, t: int) -> tuple[Image.Image, dict]:
    """3 CYCLOPEAN / EPISTEMIC state of the target AFTER action t."""
    a = ctx.actions[t]
    sm = ctx.steps[t]
    i = int(a["target_id"])
    z = ctx.step_npz(t)
    gaze = tuple(a["gaze_deg"])
    lines, nxt, nsrc = probe_lines(sm["probe_after"])
    main = V.epistemic_image(ctx.chart, z["class_code"], stipple_spacing=8)
    V.grid_lines(main, ctx.chart, labels=True)
    n_open, n_el = unresolved_marks(main, ctx.chart, z, r=3, lattice=5)
    marks_chart(main, ctx.chart, gaze, nxt, False, r=14)
    tgt = (z["class_code"] == V.CODE["TARGET_SUPPORT"])
    ys, xs = np.nonzero(tgt)
    tpts = np.c_[-25.0 + xs * D.GRID_DEG, -20.0 + ys * D.GRID_DEG] if len(xs) else np.empty((0, 2))

    def pts_fn(s):
        out = core_box_points(ctx.actions[s]["gaze_deg"], 4.0)
        pr = ctx.steps[s]["probe_after"]
        _l, nx, _s = probe_lines(pr)
        if nx is not None:
            out.append(nx)
        return out
    win = causal_window(ctx, t, pts_fn)
    ch = V.Chart(*win, INSET_W / (win[1] - win[0]))
    inset = V.epistemic_image(ch, z["class_code"], stipple_spacing=10)
    unresolved_marks(inset, ch, z, r=6, lattice=12)
    marks_chart(inset, ch, gaze, nxt if nxt and ch.inside(nxt, 2) else None, False, r=20)
    if nxt is None:
        quiet_stamp(inset, ch.w - 110, 34)
        gx, gy = ctx.chart.pt(gaze)
        quiet_stamp(main, min(max(gx + 70, 80), CHART_W - 80), min(max(gy + 44, 30), CHART_H - 30), size=S.T_BODY)
    di = ImageDraw.Draw(inset)
    di.rectangle([0, 0, ch.w - 1, ch.h - 1], outline=S.INK, width=2)
    S.text(di, (10, 8), "ZOOM", size=S.T_SMALL, bold=True, plate=S.WHITE)
    x0, y0 = ctx.chart.pt((win[0], win[3])); x1, y1 = ctx.chart.pt((win[1], win[2]))
    S.dashed_rect(ImageDraw.Draw(main), [x0, y0, x1, y1], S.INK, width=2, dash=6, gap=5)
    content = Image.new("RGB", (V.CONTENT_W, V.CONTENT_H), S.PANEL)
    content.paste(main.crop((0, 0, CHART_W, CHART_H)), (0, 0))
    content.paste(inset.resize((INSET_W, INSET_H)) if inset.size != (INSET_W, INSET_H) else inset, (CHART_W + 10, 0))
    disp = [e for e in ctx.c02_events if e["global_step"] == t and e["object"] == i and e["event"] == "deferred"]
    tail = []
    if nxt is None:
        tail.append(("QUIET: the local policy proposes nothing", {"bold": True}))
    else:
        tail.append((f"next local proposal {gaze_text(nxt)} ({SRC_LABEL[nsrc].split()[0]})", {"bold": True}))
    if disp:
        tail.append((f"ordinary budget reached ({disp[0]['fixations']} looks) → DEFERRED", {"bold": True, "fill": S.OI_VERM}))
    V.plate_lines(content, (CHART_W + 16, INSET_H + 10),
                  [("local probe after this look:", {"bold": False})] + lines + tail, size=S.T_BODY, gap=7)
    meta = {"next_proposal": nxt, "next_source": nsrc, "unresolved_open_elements": n_open, "eligible_cells": n_el,
            "epistemic_source": f"cache steps/step_{t:03d}.npz (E_t(i) recomputed; equal to saved views where saved)",
            "inset_window": list(win), "deferred_here": bool(disp)}
    return content, meta


def panel_memory(ctx: Ctx, mem: Memory, t: int) -> tuple[Image.Image, dict]:
    """4 PERSISTENT 3-D MEMORY after action t, with the delta caused by t."""
    a = ctx.actions[t]
    sm = ctx.steps[t]
    i, k = int(a["target_id"]), int(a["object_local_step"])
    z = ctx.step_npz(t)
    before = mem.maps_before
    pxyz = before[0]
    main_view = V.View3D(ctx.cam, (780, V.CONTENT_H))
    img = main_view.render(pxyz, V.depth_shade(pxyz, ctx.cam, dlim=ctx.dlim), bg=S.PANEL) if len(pxyz) else \
        np.full((V.CONTENT_H, 780, 3), S.PANEL, np.uint8)
    main = Image.fromarray(img)
    delta = np.concatenate([z["new_xyz"], z["repeated_xyz"]]) if len(z["new_xyz"]) + len(z["repeated_xyz"]) else None

    def draw_delta(view: V.View3D, im: Image.Image, big: bool):
        arr = np.asarray(im).copy()
        if len(z["new_xyz"]):
            arr = view.render(z["new_xyz"], S.OI_GREEN, img=arr, radius=1 if big else 0)
        im.paste(Image.fromarray(arr))
        lat = 14 if big else 9
        cells = view.occupied_cells(z["cross_xyz"], 2 * lat) if len(z["cross_xyz"]) else []
        V.lattice_marks(im, cells, "x", S.OI_SKY, r=4 if big else 3, width=2)
        cells = view.occupied_cells(z["repeated_xyz"], lat) if len(z["repeated_xyz"]) else []
        V.lattice_marks(im, cells, "ring", S.OI_PURPLE, r=5 if big else 3, width=2)
        if len(z["new_xyz"]) and len(z["new_xyz"]) < 400:
            x, y, _ = view.xy(z["new_xyz"])
            for xx, yy in list(zip(x, y))[:: max(1, len(x) // 60)]:
                S.square(ImageDraw.Draw(im), float(xx), float(yy), r=4 if big else 3, color=S.OI_GREEN)
    draw_delta(main_view, main, False)
    tv = np.concatenate([z["new_xyz"], z["repeated_xyz"]]) if delta is not None else np.empty((0, 3))
    gaze_end = np.median(tv, axis=0) if len(tv) else None
    V.head_glyph(main, main_view, gaze_end)
    # zoom inset around the delta (bounds grown over the bout; causal)
    b0, _ = ctx.bout_of(t)
    zpts = [ctx.step_npz(s)["new_xyz"] for s in range(b0, t + 1)] + [ctx.step_npz(s)["repeated_xyz"] for s in range(b0, t + 1)]
    zpts = np.concatenate([p for p in zpts if len(p)]) if any(len(p) for p in zpts) else None
    content = Image.new("RGB", (V.CONTENT_W, V.CONTENT_H), S.PANEL)
    iw, ih = V.CONTENT_W - 780 - 10, INSET_H
    if zpts is not None:
        zb = main_view.zoom_bounds(zpts)
        zv = V.View3D(ctx.cam, (iw, ih), bounds=zb, pad=10)
        zi = zv.render(pxyz, V.depth_shade(pxyz, ctx.cam, dlim=ctx.dlim), bg=S.PANEL) if len(pxyz) else \
            np.full((ih, iw, 3), S.PANEL, np.uint8)
        inset = Image.fromarray(zi)
        draw_delta(zv, inset, True)
        (u0, v0), (u1, v1) = zb
        corners = np.array([[u0, v0], [u1, v1]])
        cx0 = (corners[0, 0] - main_view.u0) * main_view.sc; cy0 = (corners[0, 1] - main_view.v0) * main_view.sc
        cx1 = (corners[1, 0] - main_view.u0) * main_view.sc; cy1 = (corners[1, 1] - main_view.v0) * main_view.sc
        S.dashed_rect(ImageDraw.Draw(main), [cx0, cy0, cx1, cy1], S.INK, width=2, dash=6, gap=5)
    else:
        inset = Image.new("RGB", (iw, ih), S.PANEL)
        S.text(ImageDraw.Draw(inset), (20, 20), "no target measurement", size=S.T_BODY)
    di = ImageDraw.Draw(inset)
    di.rectangle([0, 0, iw - 1, ih - 1], outline=S.INK, width=2)
    S.text(di, (10, 8), "ZOOM", size=S.T_SMALL, bold=True, plate=S.WHITE)
    content.paste(main, (0, 0))
    content.paste(inset, (790, 0))
    ncross = len(sm["cross_target_by_object"])
    V.plate_lines(content, (796, INSET_H + 10), [
        (f"active map {i}: {fmt(sm['active_map_before'])} → {fmt(sm['active_map_after'])}", {"bold": True}),
        (f"new surfels  +{fmt(sm['new_surfels'])}", {"fill": (0, 110, 80), "bold": True}),
        (f"repeated measurements  {fmt(sm['repeated_measurements'])}", {"fill": (150, 60, 115), "bold": True}),
        (f"cross-target  {fmt(sm['cross_target_points'])} ({ncross} object{'s' if ncross != 1 else ''})",
         {"fill": (0, 100, 160)}),
    ], size=S.T_BODY, gap=8)
    meta = {"new_surfels": sm["new_surfels"], "repeated_measurements": sm["repeated_measurements"],
            "cross_target_points": sm["cross_target_points"], "active_map": [sm["active_map_before"], sm["active_map_after"]],
            "geometry_source": f"maps before step {t} (latest fix_k per object) + cache steps/step_{t:03d}.npz delta"}
    return content, meta


def step_frame(ctx: Ctx, mem: Memory, t: int) -> tuple[Image.Image, dict]:
    a = ctx.actions[t]
    i = int(a["target_id"])
    mem.advance(t - 1)
    mem.maps_before = mem.union_maps()
    p1, m1 = panel_scene(ctx, mem, t)
    p2, m2 = panel_eyes(ctx, t)
    p3, m3 = panel_epistemic(ctx, t)
    mem.advance(t)
    p4, m4 = panel_memory(ctx, mem, t)
    canvas = Image.new("RGB", (V.W, V.H), S.SURFACE)
    head = f"Look {t}: {SRC_LABEL[a['action_source']]} at {i} {ctx.src.names(i)}"
    sub = ("seed from the oracle catalog" if a["action_source"] == "oracle_seed" else
           f"proposed by the accepted local policy ({SRC_LABEL[a['action_source']].split()[0]})") + \
          f" · gaze {gaze_text(a['gaze_deg'])} · {'SWITCH' if m1['switch'] else 'retain'}"
    V.header(canvas, head, sub, "NORMAL", f"STEP {t:03d} / 140")
    b1 = ["CONTROLLER-TIME"] + (["ORACLE INPUT"] if a["action_source"] == "oracle_seed" else [])
    V.panel(canvas, 0, "1", "SCENE / ATTENTION", f"BEFORE look {t}", b1, p1)
    V.panel(canvas, 1, "2", "THE EYES", f"OBSERVATION by look {t}", ["CONTROLLER-TIME", "ORACLE INPUT"], p2)
    V.panel(canvas, 2, "3", "CYCLOPEAN / EPISTEMIC", f"AFTER look {t}", ["DERIVED"], p3)
    V.panel(canvas, 3, "4", "PERSISTENT 3-D MEMORY", f"AFTER look {t}", ["CONTROLLER-TIME"], p4)
    V.roster(canvas, states_after(ctx, t), i)
    V.timeline(canvas, ctx.actions, ctx.c02_events, t)
    meta = {"kind": "step", "global_step": t, "target_id": i, "target_name": ctx.src.names(i),
            "action_source": a["action_source"], "gaze_deg": a["gaze_deg"], "phase": "NORMAL",
            "service_state_after": ctx.src.c02_actions[t]["service_states_after"][str(i)],
            "panels": {"1": {"badges": b1, **m1}, "2": {"badges": ["CONTROLLER-TIME", "ORACLE INPUT"], **m2},
                       "3": {"badges": ["DERIVED"], **m3}, "4": {"badges": ["CONTROLLER-TIME"], **m4}},
            "new_surfels": ctx.steps[t]["new_surfels"], "repeated_target_measurements": ctx.steps[t]["repeated_measurements"],
            "target_valid_points": ctx.steps[t]["target_valid_points"],
            "observation_source_files": m2["observation_files"], "epistemic_state_source": m3["epistemic_source"],
            "geometry_state_source": m4["geometry_source"],
            "truth": sorted(set(b1) | {"CONTROLLER-TIME", "ORACLE INPUT", "DERIVED"}),
            "hold_frames": HOLD["switch"] if m1["switch"] else HOLD["ordinary"]}
    return canvas, meta


def prepare_camera(src: D.Sources, cache: Path) -> dict:
    """The standard 3-D camera framed once on the final active maps (fixed for every frame)."""
    xyz = np.concatenate([np.asarray(D.load_npz(src.obj_dir(int(o["instance_id"])) / "final_map.npz")["xyz_h"], np.float64)
                          for o in src.manifest["objects"]])
    cam = V.Camera3D()
    bounds = cam.fit(xyz, 0.5, 99.5)
    _u, _v, dd = cam.project(xyz)
    out = {"elev_deg": V.Camera3D.ELEV, "azim_deg": V.Camera3D.AZIM, "bounds": bounds,
           "depth_limits": [float(np.percentile(dd, 1)), float(np.percentile(dd, 99))], "points": int(len(xyz))}
    D.write_json(cache / "camera.json", out)
    return out


# ---------------------------------------------------------------- special frames: shared pieces

def blank_content(text=""):
    im = Image.new("RGB", (V.CONTENT_W, V.CONTENT_H), (244, 243, 239))
    if text:
        S.text(ImageDraw.Draw(im), (V.CONTENT_W // 2, V.CONTENT_H // 2), text, size=S.T_HEAD, fill=S.MUTED,
               outline=None, anchor="mm")
    return im


def event_canvas(ctx: Ctx, headline, sub, phase, step_text, states, current, highlight=None, phase_cells=None,
                 timeline_current=None):
    canvas = Image.new("RGB", (V.W, V.H), S.SURFACE)
    V.header(canvas, headline, sub, phase, step_text)
    V.roster(canvas, states, current)
    V.timeline(canvas, ctx.actions, ctx.c02_events, timeline_current, highlight=highlight, phase_cells=phase_cells)
    return canvas


def banner(canvas: Image.Image, lines, y=1100, color=S.INK, fill=S.WHITE, xc=V.W / 2):
    d = ImageDraw.Draw(canvas)
    f = S.font(S.T_TITLE, True)
    widths = [d.textlength(s, font=f) for s in lines]
    w = max(widths) + 60
    h = len(lines) * (S.T_TITLE + 14) + 28
    x0 = xc - w / 2
    d.rectangle([x0, y - h, x0 + w, y], fill=fill, outline=color, width=4)
    for n, s in enumerate(lines):
        d.text((xc - widths[n] / 2, y - h + 16 + n * (S.T_TITLE + 14)), s, font=f, fill=color)


def big_panel(canvas: Image.Image, box, title, badges, content: Image.Image, tag=""):
    x0, y0, x1, y1 = box
    d = ImageDraw.Draw(canvas)
    d.rectangle(box, fill=S.PANEL, outline=(205, 204, 199), width=2)
    d.rectangle([x0, y0, x1, y0 + V.TITLE_H], fill=(238, 237, 233))
    d.text((x0 + 12, y0 + 8), title, font=S.font(S.T_HEAD, True), fill=S.INK)
    if tag:
        tx = x0 + 12 + d.textlength(title, font=S.font(S.T_HEAD, True)) + 16
        f = S.font(S.T_SMALL, True)
        d.rectangle([tx, y0 + 9, tx + d.textlength(tag, font=f) + 16, y0 + 38], fill=S.INK)
        d.text((tx + 8, y0 + 12), tag, font=f, fill=S.WHITE)
    bx = x1 - 10
    for b in reversed(badges):
        bx = S.badge(canvas, bx, y0 + 7, b) - 8
    cw, chh = x1 - x0 - 4, y1 - y0 - V.TITLE_H - 4
    bg = Image.new("RGB", (cw, chh), S.PANEL)
    bg.paste(content.crop((0, 0, min(cw, content.width), min(chh, content.height))), (0, 0))
    canvas.paste(bg, (x0 + 2, y0 + V.TITLE_H + 2))


def final_maps(ctx: Ctx):
    xyz, rgb, ids = [], [], []
    for o in ctx.src.manifest["objects"]:
        i = int(o["instance_id"])
        z = D.load_npz(ctx.src.obj_dir(i) / "final_map.npz")
        xyz.append(np.asarray(z["xyz_h"], np.float32)); rgb.append(D.gamma_u8(z["rgb"]))
        ids.append(np.full(len(z["xyz_h"]), i, np.int32))
    return np.concatenate(xyz), np.concatenate(rgb), np.concatenate(ids)


def state_chart(ctx: Ctx, chart: V.Chart, xyz, ids, deferred=(), residual=(), labels=()):
    """Final active maps colored by service state (QUIET slate; DEFERRED / RESIDUAL hatched)."""
    img = V.splat(chart, xyz, S.SLATE, radius=1 if chart.s < 20 else 2)
    im = Image.fromarray(img)
    for i, kind in [(j, "DEFERRED") for j in deferred] + [(j, "RESIDUAL") for j in residual]:
        m = V.splat(chart, xyz[ids == i], (255, 255, 255), img=np.zeros((chart.h, chart.w, 3), np.uint8),
                    radius=1 if chart.s < 20 else 2).any(-1)
        arr = np.asarray(im).copy()
        arr[m] = (253, 243, 222) if kind == "DEFERRED" else (250, 232, 220)
        im = Image.fromarray(arr)
        S.hatch(im, (0, 0, chart.w, chart.h), S.OI_ORANGE if kind == "DEFERRED" else S.OI_VERM, spacing=10, width=3,
                cross=kind == "RESIDUAL", mask=Image.fromarray((m * 255).astype(np.uint8)))
        V.outline(im, m, S.OI_ORANGE if kind == "DEFERRED" else S.OI_VERM, width=4)
        if kind == "RESIDUAL":
            V.outline(im, m, S.INK, width=1)
    d = ImageDraw.Draw(im)
    for i, text in labels:
        yy, pp = D.angles(xyz[ids == i])
        x, y = chart.pt((float(np.median(yy)), float(np.quantile(pp, 0.8))))
        S.text(d, (x, y), text, size=S.T_BODY, bold=True, plate=S.WHITE, anchor="mm")
    return im


# ---------------------------------------------------------------- bootstrap

def bootstrap_stages(ctx: Ctx):
    src = ctx.src
    n_cat, n_loc = len(src.catalog), len(src.seeds)
    n_unl = len(src.c02_result["terminal"]["unlocated"])
    states = {i: "SEEDABLE" for i in src.seeds}
    ch = V.Chart(-25.0, 25.0, -20.0, 20.0, 1600 / 50.0)
    stages = []
    for stage in (1, 2):
        canvas = event_canvas(ctx, "Bootstrap: the initial object catalog (oracle)",
                              "current oracle boundary: the Blender scene graph supplies the catalog and one seed per localized object",
                              "NORMAL", "BOOTSTRAP", states, None)
        im = Image.new("RGB", (ch.w, ch.h), UNMEASURED)
        V.grid_lines(im, ch, labels=True)
        d = ImageDraw.Draw(im)
        if stage == 2:
            for i, g in sorted(src.seeds.items()):
                x, y = ch.pt(g)
                d.rectangle([x - 9, y - 9, x + 9, y + 9], fill=S.INK2, outline=S.WHITE, width=2)
                S.text(d, (x + 13, y - 13), str(i), size=S.T_SMALL, bold=True)
        S.text(d, (16, 12), "head-centred chart of the controller domain (yaw ±25°, pitch ±20°): nothing measured yet",
               size=S.T_BODY, plate=S.WHITE)
        big_panel(canvas, (16, 92, 16 + 1604, 92 + 1100), "SEED DIRECTIONS", ["ORACLE INPUT"],
                  im.resize((1600, 1050)) if stage else im, tag="BEFORE look 0")
        right = Image.new("RGB", (V.W - 1650 - 20, 1050), S.PANEL)
        lines = [(f"{n_cat}", {"bold": True, "size": S.T_HUGE}), ("objects in the Blender scene graph (catalog)", {}),
                 ("", {"size": 12})]
        if stage == 2:
            lines += [(f"{n_loc}", {"bold": True, "size": S.T_HUGE}),
                      ("localized: visible inside the controller domain", {}), ("(seed scan by ray casting in Blender)", {"fill": S.INK2}),
                      ("", {"size": 12}),
                      (f"{n_loc} seeds", {"bold": True, "size": S.T_BIG}), ("one gaze direction per localized object", {}),
                      ("", {"size": 12}),
                      (f"{n_unl}", {"bold": True, "size": S.T_HUGE}), ("unlocated: never become controller targets", {}),
                      ("", {"size": 12}),
                      ("all 25 are initialized later by their", {"bold": True}), ("first (seed) look", {"bold": True}),
                      ("", {"size": 12}),
                      ("dense evaluation truth is not used", {"fill": S.INK2})]
        V.plate_lines(right, (24, 24), lines, size=S.T_BODY, gap=6)
        big_panel(canvas, (1636, 92, V.W - 16, 92 + 1100), "WHAT THE ORACLE SUPPLIES", ["ORACLE INPUT"], right)
        stages.append(canvas)
    meta = {"kind": "special", "event": "bootstrap", "catalog": n_cat, "localized": n_loc, "unlocated": n_unl,
            "seeds": {str(k): list(v) for k, v in src.seeds.items()}, "truth": ["ORACLE INPUT"], "phase": "NORMAL"}
    return stages, meta


# ---------------------------------------------------------------- natural reactivations

def reactivation_stages(ctx: Ctx, obj: int):
    ev = ctx.events[str(obj)]
    z = D.load_npz(ctx.cache / f"events_reactivation_{obj:04d}.npz")
    q, r, trig, served = ev["quiet_since"], ev["reactivated_after"], ev["trigger"], ev["served"]
    name = ctx.src.names(obj)
    after_states = states_after(ctx, r)
    # window around the object's support
    sup = np.argwhere(z["after_class"] == V.CODE["TARGET_SUPPORT"])
    el = np.argwhere(z["eligible_after"])
    pts = np.r_[np.c_[-25.0 + sup[:, 1] * 0.1, -20.0 + sup[:, 0] * 0.1], np.c_[-25.0 + el[:, 1] * 0.1, -20.0 + el[:, 0] * 0.1],
                [ev["proposal_after"]]]
    win = V.fit_window(pts, min_w=12.0, aspect=V.CONTENT_W / V.CONTENT_H, margin=1.5)
    ch = V.Chart(*win, V.CONTENT_W / (win[1] - win[0]))

    def epi(class_code, eligible, proposal, label):
        im = V.epistemic_image(ch, class_code, stipple_spacing=10)
        zz = {"frontier_yaw_pitch": np.empty((0, 2)), "frontier_state": np.empty(0), "eligible": eligible}
        unresolved_marks(im, ch, zz, r=7, lattice=12)
        own = [a["gaze_deg"] for a in ctx.actions[:r + 1] if a["target_id"] == obj]
        d = ImageDraw.Draw(im)
        for g in own:
            x, y = ch.pt(g)
            S.xmark(d, x, y, r=7, color=S.INK, width=3)
        if proposal is not None:
            x, y = ch.pt(proposal)
            S.crosshair(d, x, y, r=20, solid=False)
            S.text(d, (x + 30, y - 40), f"Cyclopean proposal {gaze_text(proposal)}", size=S.T_BODY, bold=True, plate=S.WHITE)
        S.text(d, (14, 12), label, size=S.T_HEAD, bold=True, plate=S.WHITE)
        return im
    p1 = epi(z["before_class"], z["eligible_before"], None,
             f"{obj} QUIET since look {q}: eligible cells {ev['eligible'][0]}")
    quiet_stamp(p1, V.CONTENT_W - 120, 90)
    p3 = epi(z["after_class"], z["eligible_after"], ev["proposal_after"],
             f"after look {r}: eligible cells {ev['eligible'][1]} → ACTIONABLE")
    # the trigger observation, with the object's pixels ringed and magnified
    ta = ctx.actions[r]
    Lr, _Rr = ctx.src.benchmark(trig, int(ta["object_local_step"]))
    patch = ctx.src.patch(trig, int(ta["object_local_step"]))
    m = patch["valid"] & (patch["instance_id"] == obj)
    sz = 480
    L = np.asarray(Image.fromarray(Lr).resize((sz, sz), Image.LANCZOS)).astype(np.float32)
    mm = cv2.resize(m.astype(np.uint8), (sz, sz), interpolation=cv2.INTER_NEAREST) > 0
    L[mm] = L[mm] * 0.2 + np.array(S.OI_SKY) * 0.8
    left = Image.fromarray(L.astype(np.uint8))
    V.outline(left, cv2.resize((patch["instance_id"] == trig).astype(np.uint8), (sz, sz),
                               interpolation=cv2.INTER_NEAREST) > 0, S.INK, width=2, halo=S.WHITE)
    V.outline(left, mm, S.OI_SKY, width=3, halo=S.INK)
    content2 = Image.new("RGB", (V.CONTENT_W, V.CONTENT_H), S.PANEL)
    content2.paste(left, (0, 10))
    d2 = ImageDraw.Draw(content2)
    px = np.argwhere(m)
    if len(px) <= 50:
        for yy, xx in px:
            S.ring(d2, xx * sz / 256 + sz / 512, 10 + yy * sz / 256 + sz / 512, r=18, color=S.OI_SKY, width=4)
        cy, cx = px.mean(axis=0)
        half = 8
        y0 = int(min(max(0, round(cy) - half), m.shape[0] - 2 * half))
        x0 = int(min(max(0, round(cx) - half), m.shape[1] - 2 * half))
        crop = Lr[y0:y0 + 2 * half, x0:x0 + 2 * half].copy()
        cm = m[y0:y0 + 2 * half, x0:x0 + 2 * half]
        crop[cm] = S.OI_SKY
        mag = Image.fromarray(crop).resize((2 * half * 22, 2 * half * 22), Image.NEAREST)
        dm = ImageDraw.Draw(mag)
        for yy, xx in np.argwhere(cm):
            dm.rectangle([xx * 22, yy * 22, xx * 22 + 21, yy * 22 + 21], outline=S.INK, width=3)
        content2.paste(mag, (sz + 30, 10))
        d2.rectangle([sz + 30, 10, sz + 30 + mag.width - 1, 10 + mag.height - 1], outline=S.INK, width=3)
        S.text(d2, (sz + 40, 18), f"MAGNIFIED ×22: the {len(px)} pixels", size=S.T_BODY, bold=True, plate=S.WHITE)
        d2.rectangle([x0 * sz / 256, 10 + y0 * sz / 256, (x0 + 2 * half) * sz / 256, 10 + (y0 + 2 * half) * sz / 256],
                     outline=S.INK, width=2)
        d2.line([(x0 + 2 * half) * sz / 256, 10 + y0 * sz / 256, sz + 30, 10], fill=S.INK, width=2)
        tx = sz + 30
    else:
        tx = sz + 30
        V.plate_lines(content2, (tx, 20), [(f"{fmt(len(px))} pixels of {obj} in this look", {"bold": True})], size=S.T_BODY)
    V.plate_lines(content2, (tx, 390), [
        (f"look {r} targets {trig} {ctx.src.names(trig)}", {"bold": True}),
        f"it measures {fmt(ev['trigger_look_points'])} points of {obj} (cross-target)",
    ], size=S.T_BODY, gap=8)
    # persistent memory of the object: effective geometry before / after
    before = z["before_xyz"]
    added = z["added_xyz"]
    view = V.View3D(ctx.cam, (760, V.CONTENT_H))
    zb = view.zoom_bounds(np.r_[before, added] if len(before) else added, margin=0.3)
    if len(added) <= 50:  # a handful of points must stay inside the frame
        ua, va, _ = ctx.cam.project(added)
        zb = ([min(zb[0][0], ua.min() - 0.2), min(zb[0][1], va.min() - 0.2)],
              [max(zb[1][0], ua.max() + 0.2), max(zb[1][1], va.max() + 0.2)])
    zv = V.View3D(ctx.cam, (760, V.CONTENT_H), bounds=zb, pad=30)
    img4 = Image.fromarray(zv.render(before, V.depth_shade(before, ctx.cam, dlim=ctx.dlim)))
    d4 = ImageDraw.Draw(img4)
    if len(added) <= 50:
        x, y, _ = zv.xy(added)
        for xx, yy in zip(x, y):
            S.xmark(d4, float(xx), float(yy), r=9, color=S.OI_SKY, width=4)
            S.ring(d4, float(xx), float(yy), r=22, color=S.INK, width=3)
    else:
        V.lattice_marks(img4, zv.occupied_cells(added, 16), "x", S.OI_SKY, r=5, width=2)
    content4 = Image.new("RGB", (V.CONTENT_W, V.CONTENT_H), S.PANEL)
    content4.paste(img4, (0, 0))
    by = ", ".join(f"{fmt(n)} from {k}" for k, n in ev["added_by_source"].items())
    V.plate_lines(content4, (780, 20), [
        ("effective geometry", {"bold": True}),
        (f"{fmt(ev['effective'][0])} → {fmt(ev['effective'][1])}", {"bold": True, "size": S.T_BIG}),
        (f"+{fmt(ev['added'])} cross-target points", {"fill": (0, 100, 160), "bold": True}),
        (by, {"size": S.T_SMALL}),
        (f"looks {', '.join(map(str, ev['added_steps']))}", {"size": S.T_SMALL}),
        ("own looks since quiet: 0", {"size": S.T_SMALL}),
        ("", {"size": 10}),
        ("active map unchanged: only", {}), ("measurement memory grew", {}),
        ("", {"size": 10}),
        (f"ACTIONABLE → serviced at look {served}", {"bold": True}),
    ], size=S.T_BODY, gap=6)
    titles = [("1", f"{obj} {name}: QUIET", f"since look {q}", ["DERIVED"], p1),
              ("2", f"look {r}: {trig} {ctx.src.names(trig)}", "OBSERVATION", ["CONTROLLER-TIME", "ORACLE INPUT"], content2),
              ("3", "Cyclopean state of " + str(obj), f"AFTER look {r}", ["DERIVED"], p3),
              ("4", f"3-D memory of {obj}", f"AFTER look {r}", ["CONTROLLER-TIME"], content4)]
    stages = []
    for k in range(1, 5):
        canvas = event_canvas(ctx, f"Natural reactivation of {obj} {name}",
                              f"QUIET (look {q}) → look {r} at {trig} → {fmt(ev['added'])} cross-target points → "
                              f"eligible {ev['eligible'][0]} → {ev['eligible'][1]} → ACTIONABLE → serviced (look {served})",
                              "NORMAL", f"AFTER STEP {r:03d}", after_states, obj, highlight=(q, r), timeline_current=r)
        for n, (num, title, tag, badges, content) in enumerate(titles):
            if n < k:
                V.panel(canvas, n, num, title, tag, badges, content)
            else:
                V.panel(canvas, n, num, title, tag, [], blank_content("…"))
        if k == 4:
            banner(canvas, ["cross-object evidence changed the local state:",
                            f"{obj} QUIET → ACTIONABLE, with no look of its own"], y=1186, xc=V.PANEL_XY[3][0] + 860)
        stages.append(canvas)
    meta = {"kind": "special", "event": f"reactivation_{obj}", "object": obj, "target_name": name, "phase": "NORMAL",
            "global_step": r, **{k: ev[k] for k in ("quiet_since", "reactivated_after", "trigger", "effective", "eligible",
                                                 "added", "added_by_source", "added_steps", "served", "trigger_look_points")},
            "truth": ["CONTROLLER-TIME", "DERIVED", "ORACLE INPUT"]}
    return stages, meta


# ---------------------------------------------------------------- deferral of 210

def defer_stages(ctx: Ctx):
    e = [x for x in ctx.c02_events if x["event"] == "deferred"]
    ev = e[0]
    s, obj = int(ev["global_step"]), int(ev["object"])
    name = ctx.src.names(obj)
    looks = [a for a in ctx.actions[:s + 1] if a["target_id"] == obj]
    img, inst = ctx.raster(s)
    win = V.fit_window(np.array([a["gaze_deg"] for a in looks] + [[7.6, 18.2]]), min_w=20, aspect=V.CONTENT_W / V.CONTENT_H,
                       margin=5.0)
    ch = V.Chart(*win, V.CONTENT_W / (win[1] - win[0]))
    # 1: the 24 ordinary looks over the measurement memory
    full = Image.fromarray(lighten(img, 0.35))
    x0, y0 = ctx.chart.pt((win[0], win[3])); x1, y1 = ctx.chart.pt((win[1], win[2]))
    p1 = full.crop((int(x0), int(y0), int(x1), int(y1))).resize((V.CONTENT_W, V.CONTENT_H), Image.LANCZOS)
    tm = cv2.resize((inst == obj).astype(np.uint8)[int(y0):int(y1), int(x0):int(x1)], (V.CONTENT_W, V.CONTENT_H),
                    interpolation=cv2.INTER_NEAREST)
    V.outline(p1, tm > 0, S.INK, width=3, halo=S.WHITE)
    d = ImageDraw.Draw(p1)
    for n, a in enumerate(looks):
        x, y = ch.pt(a["gaze_deg"])
        _lab, col, shape = S.SOURCES[a["action_source"]]
        r = 11
        if shape == "square":
            d.rectangle([x - r, y - r, x + r, y + r], fill=col, outline=S.WHITE, width=2)
        elif shape == "circle":
            d.ellipse([x - r, y - r, x + r, y + r], fill=col, outline=S.WHITE, width=2)
        else:
            d.polygon([(x, y - r - 2), (x + r + 2, y), (x, y + r + 2), (x - r - 2, y)], fill=col, outline=S.WHITE)
        S.text(d, (x + 12, y - 26), str(n + 1), size=S.T_SMALL, bold=True)
    S.text(d, (14, 12), f"{len(looks)} ordinary looks of {obj} (numbered; shape = source)", size=S.T_HEAD, bold=True, plate=S.WHITE)
    # 2: after look 24 the local policy still proposes a look
    z = ctx.step_npz(s)
    p2 = V.epistemic_image(ch, z["class_code"], stipple_spacing=10)
    unresolved_marks(p2, ch, z, r=6, lattice=11)
    pr = ctx.steps[s]["probe_after"]["fsg6f"]
    marks_chart(p2, ch, tuple(looks[-1]["gaze_deg"]), tuple(pr["next_gaze_deg"]), False, r=20)
    d = ImageDraw.Draw(p2)
    S.text(d, (14, 12), f"after look {len(looks)}: FSG6f continue · OPEN {pr['frontier_open_count']} · proposal "
           f"{gaze_text(pr['next_gaze_deg'])}", size=S.T_HEAD, bold=True, plate=S.WHITE)
    S.text(d, (14, 56), "local state: ACTIONABLE (it still wants a look)", size=S.T_BODY, plate=S.WHITE)
    # 3: the disposition
    p3 = Image.new("RGB", (V.CONTENT_W, V.CONTENT_H), S.PANEL)
    S.state_tile(p3, (40, 60, 330, 190), "ACTIONABLE", f"{obj}", size=S.T_BIG)
    d = ImageDraw.Draw(p3)
    S.arrow(d, 350, 125, 520, 125, width=5, head=22)
    S.text(d, (360, 70), f"{ev['fixations']} looks = budget", size=S.T_SMALL, bold=True)
    S.state_tile(p3, (540, 60, 830, 190), "DEFERRED", f"{obj}", size=S.T_BIG)
    V.plate_lines(p3, (40, 215), [
        ("disposition DEFERRED (reason: ordinary budget)", {"bold": True}),
        ("local state stays ACTIONABLE; it gets no more ordinary looks", {}),
    ], size=S.T_BODY, gap=8)
    S.state_tile(p3, (40, 330, 250, 420), "QUIET", "QUIET", size=S.T_BODY)
    S.text(d, (275, 342), "≠", size=64, bold=True, outline=None)
    S.state_tile(p3, (340, 330, 590, 420), "DEFERRED", "DEFERRED", size=S.T_BODY)
    V.plate_lines(p3, (620, 330), [("QUIET: nothing left to do", {}), ("DEFERRED: still wants a look,", {}),
                                   ("       set aside for now", {})], size=S.T_BODY, gap=6)
    # 4: the scene keeps going
    p4 = Image.new("RGB", (V.CONTENT_W, V.CONTENT_H), S.PANEL)
    later = ctx.actions[s + 1:]
    V.plate_lines(p4, (30, 20), [
        ("the rest of the scene keeps going", {"bold": True, "size": S.T_HEAD}),
        (f"{len(later)} more ordinary looks after look {s}, none for {obj}", {}),
    ], size=S.T_BODY, gap=8)
    xx, yy = 30, 120
    prev = None
    d = ImageDraw.Draw(p4)
    for a in later:
        if a["target_id"] != prev:
            prev = a["target_id"]
            n = sum(1 for b in later if b["target_id"] == prev)
            lab = f"{prev} {ctx.src.names(prev)}"
            tw = d.textlength(lab, font=S.font(S.T_BODY, True)) + 24
            if xx + tw > V.CONTENT_W - 20:
                xx, yy = 30, yy + 64
            st = V.tile_state(ctx.src.c02_actions[a["global_step"]]["service_states_before"][str(prev)])
            S.state_tile(p4, (xx, yy, xx + tw, yy + 50), st, lab, size=S.T_BODY)
            xx += tw + 12
    V.plate_lines(p4, (30, yy + 80), [("209 unlocated objects are never targets; 210 stays DEFERRED until the residue phase", {"size": S.T_SMALL})])
    titles = [("1", f"{obj} {name}", f"looks up to {s}", ["CONTROLLER-TIME"], p1),
              ("2", "local epistemic state", f"AFTER look {s}", ["DERIVED"], p2),
              ("3", "disposition", f"AT look {s}", ["CONTROLLER-TIME"], p3),
              ("4", "scene continues", f"looks {s + 1}..{len(ctx.actions) - 1}", ["CONTROLLER-TIME"], p4)]
    stages = []
    for k in range(1, 5):
        canvas = event_canvas(ctx, f"{obj} {name} is DEFERRED at look {s}",
                              f"local ACTIONABLE · ordinary look count {ev['fixations']} = budget → disposition DEFERRED "
                              "(Controller-01 had BLOCKED it)", "NORMAL", f"AFTER STEP {s:03d}", states_after(ctx, s), obj,
                              highlight=(s, len(ctx.actions) - 1) if k == 4 else (looks[0]["global_step"], s), timeline_current=s)
        for n, (num, title, tag, badges, content) in enumerate(titles):
            V.panel(canvas, n, num, title, tag, badges if n < k else [], content if n < k else blank_content("…"))
        if k >= 3:
            banner(canvas, ["DEFERRED ≠ QUIET"], y=1188)
        stages.append(canvas)
    meta = {"kind": "special", "event": "defer_210", "object": obj, "global_step": s, "fixations": ev["fixations"],
            "local_state": ev["local_state"], "reason": ev["reason"], "phase": "NORMAL", "own_looks": len(looks),
            "proposal_after": pr["next_gaze_deg"], "open_after": pr["frontier_open_count"],
            "truth": ["CONTROLLER-TIME", "DERIVED"]}
    return stages, meta


# ---------------------------------------------------------------- end of the normal phase

def residue_stages(ctx: Ctx):
    last = ctx.n - 1
    end = ctx.src.c02_actions[last]["service_states_after"]
    quiet = sorted(int(k) for k, v in end.items() if v == "QUIET")
    deferred = sorted(int(k) for k, v in end.items() if "DEFERRED" in v)
    xyz, _rgb, ids = final_maps(ctx)
    ch = V.Chart(-25.0, 25.0, -20.0, 20.0, 1600 / 50.0)
    stages = []
    for k, phase in ((1, "NORMAL"), (2, "RESIDUE")):
        canvas = event_canvas(ctx, "End of the normal phase" if k == 1 else "NORMAL → RESIDUE",
                              "ordinary work is exhausted after look 140; one object keeps local residue",
                              phase, "AFTER STEP 140", states_after(ctx, last), None,
                              phase_cells={"RESIDUE": "current"} if k == 2 else None, timeline_current=last)
        im = state_chart(ctx, ch, xyz, ids, deferred=deferred,
                         labels=[(d_, f"{d_} {ctx.src.names(d_)}: ACTIONABLE + DEFERRED") for d_ in deferred])
        V.grid_lines(im, ch, labels=True)
        big_panel(canvas, (16, 92, 16 + 1604, 92 + 1100), "FINAL ACTIVE FUSED MAPS BY SERVICE STATE", ["CONTROLLER-TIME"],
                  im.resize((1600, 1050)), tag="AFTER look 140")
        right = Image.new("RGB", (V.W - 1650 - 20, 1050), S.PANEL)
        S.state_tile(right, (24, 30, 240, 120), "QUIET", f"{len(quiet)}", size=S.T_BIG)
        S.text(ImageDraw.Draw(right), (260, 55), "objects QUIET", size=S.T_HEAD, bold=True, outline=None)
        S.state_tile(right, (24, 150, 240, 240), "DEFERRED", f"{len(deferred)}", size=S.T_BIG)
        S.text(ImageDraw.Draw(right), (260, 160), "ACTIONABLE + DEFERRED", size=S.T_HEAD, bold=True, outline=None)
        S.text(ImageDraw.Draw(right), (260, 198), ", ".join(f"{d_} {ctx.src.names(d_)}" for d_ in deferred), size=S.T_BODY,
               outline=None)
        lines = [("", {"size": 20}), ("no NORMAL object is ACTIONABLE or", {}), ("SEEDABLE any more", {}), ("", {"size": 20})]
        if k == 2:
            lines += [("phase NORMAL → RESIDUE", {"bold": True, "size": S.T_BIG}),
                      ("each deferred object gets one decision:", {}), ("at most one strictly justified final look", {}),
                      ("", {"size": 20}),
                      ("ordinary work exhausted", {"bold": True}), ("≠ global quiescence", {"bold": True})]
        V.plate_lines(right, (24, 270), lines, size=S.T_BODY, gap=8)
        big_panel(canvas, (1636, 92, V.W - 16, 92 + 1100), "SCENE STATE", ["CONTROLLER-TIME"], right)
        stages.append(canvas)
    meta = {"kind": "special", "event": "residue", "phase": "NORMAL->RESIDUE", "quiet": quiet, "deferred": deferred,
            "truth": ["CONTROLLER-TIME"]}
    return stages, meta


# ---------------------------------------------------------------- the strict final-look gate

def core_outline(cal: dict, side: str, depth_m: float) -> np.ndarray:
    """The predicted rectified core's boundary as head-frame yaw/pitch at ``depth_m`` (no render)."""
    from fov3d.stereo.core import rectification
    r = rectification(cal)
    x, y, w, h = (int(v) for v in r["crop_xywh"])
    k = np.asarray(r["P1" if side == "L" else "P2"], float)[:, :3]
    rr = np.asarray(r["R1" if side == "L" else "R2"], float)
    eye = cal["eyes"][0 if side == "L" else 1]
    us = np.r_[np.linspace(0, w - 1, 40), np.full(40, w - 1), np.linspace(w - 1, 0, 40), np.zeros(40)] + x
    vs = np.r_[np.zeros(40), np.linspace(0, h - 1, 40), np.full(40, h - 1), np.linspace(h - 1, 0, 40)] + y
    rays = np.asarray(eye["R_hc"], float) @ (rr.T @ np.linalg.solve(k, np.vstack([us, vs, np.ones_like(us)])))
    rays /= np.linalg.norm(rays, axis=0)
    pts = np.asarray(eye["centre_h_m"], float)[:, None] + depth_m * rays
    yaw, pitch = D.angles(pts.T)
    return np.c_[yaw, pitch]


def gate_numbers(ctx: Ctx) -> dict:
    r0 = ctx.src.c02_residue[0]
    dd = r0["detail"]
    els = dd["elements"]
    c = dd["counts"]
    ok = (c["support"] == len(els) and c["in_both_cores"] == sum(e["in_both_cores"] for e in els)
          and c["previously_interrogated"] == sum(e["previously_interrogated"] for e in els)
          and c["novel_service_count"] == sum(e["novel"] for e in els))
    if not ok:
        raise D.ExtractionMismatch("final-gate element flags disagree with the recorded counts")
    return {"object": r0["object"], "source": r0["proposal"]["source"], "gaze": r0["proposal"]["gaze_deg"],
            "current_gaze": dd["current_gaze_deg"], "support": c["support"], "in_both_cores": c["in_both_cores"],
            "previously_interrogated": c["previously_interrogated"], "novel_service_count": c["novel_service_count"],
            "admissible": r0["admissible"], "reason": r0["reason"], "outcome": r0["outcome"],
            "final_residue_observations": ctx.src.c02_result["final_residue_observations"]}


def gate_stages(ctx: Ctx):
    g = gate_numbers(ctx)
    r0 = ctx.src.c02_residue[0]
    dd = r0["detail"]
    els = dd["elements"]
    cal = dd["predicted_calibration"]
    cur, prop = tuple(g["current_gaze"]), tuple(g["gaze"])
    ex = np.array([e["x_yaw_pitch_deg"] for e in els]); tx = np.array([e["t_yaw_pitch_deg"] for e in els])
    depth = float(np.median([np.linalg.norm(e["t_e"]) for e in els]))
    cores = {s: core_outline(cal, s, depth) for s in ("L", "R")}
    pts = np.r_[ex, tx, [cur, prop], cores["L"], cores["R"]]
    win = V.fit_window(pts, min_w=24, aspect=1600 / 1050, margin=2.0, clip=((-45.0, 45.0), (-35.0, 35.0)))
    ch = V.Chart(*win, 1600 / (win[1] - win[0]))
    view = D.load_npz(ctx.cache / "final/view_0210.npz")["class_code"]
    polys = {}
    for s in ("L", "R"):
        xs, ys = ch.px(cores[s][:, 0], cores[s][:, 1])
        polys[s] = list(zip(xs.tolist(), ys.tolist()))
    masks = []
    for s in ("L", "R"):
        m = Image.new("L", (ch.w, ch.h), 0)
        ImageDraw.Draw(m).polygon(polys[s], fill=255)
        masks.append(np.asarray(m) > 0)
    both = masks[0] & masks[1]
    fr = D.load_npz(ctx.cache / "final/frontier_0210.npz")
    names = ["unchanged FSG6f proposal", "30 OPEN support elements", "predicted left / right depth cores",
             "previously interrogated", "novel_service_count", "REJECT"]
    stages = []
    for k in range(1, 7):
        im = V.epistemic_image(ch, view, stipple_spacing=12)
        V.grid_lines(im, ch, labels=True)
        d = ImageDraw.Draw(im)
        opened = fr["yaw_pitch"][fr["state"] == 0]
        for yy, pp in opened:
            x, y = ch.pt((yy, pp))
            S.ring(d, x, y, r=5, color=S.OI_VERM, width=1)
        if k >= 3:
            arr = np.asarray(im).astype(np.float32)
            arr[both] = arr[both] * 0.55 + np.array((214, 236, 226)) * 0.45
            im.paste(Image.fromarray(arr.astype(np.uint8)))
            d = ImageDraw.Draw(im)
            for s in ("L", "R"):
                pl = polys[s]
                S.dashed_line(d, pl + [pl[0]], S.WHITE, width=7, dash=14, gap=8)
                S.dashed_line(d, pl + [pl[0]], S.CORE_GREEN, width=4, dash=14, gap=8)
            xl, yl = ch.pt((cores["L"][:, 0].min(), cores["L"][:, 1].max()))
            S.text(d, (xl + 8, yl + 8), "predicted depth cores (L, R): no render", size=S.T_BODY, bold=True, plate=S.WHITE,
                   fill=S.CORE_GREEN)
        if k >= 2:
            for e in els:
                x0, y0 = ch.pt(e["x_yaw_pitch_deg"]); x1, y1 = ch.pt(e["t_yaw_pitch_deg"])
                d.line([x0, y0, x1, y1], fill=S.OI_VERM, width=2)
                S.ring(d, x0, y0, r=8, color=S.OI_VERM, width=3)
                S.xmark(d, x1, y1, r=5, color=S.OI_VERM, width=3)
                if k >= 4 and e["previously_interrogated"]:
                    S.ring(d, x1, y1, r=13, color=S.OI_PURPLE, width=3, dashed=True)
            sx, sy = ch.pt((float(ex[:, 0].min()), float(ex[:, 1].min())))
            S.text(d, (sx - 10, sy + 30), f"{g['support']} OPEN support elements (ring = element, x = its unresolved target)",
                   size=S.T_BODY, bold=True, plate=S.WHITE, fill=S.OI_VERM)
            if k >= 4:
                S.text(d, (sx - 10, sy + 66), f"dashed purple: previously interrogated binocularly ({g['previously_interrogated']})",
                       size=S.T_BODY, plate=S.WHITE, fill=(150, 60, 115))
        x, y = ch.pt(cur)
        S.crosshair(d, x, y, r=22, solid=True)
        S.text(d, (x - 20, y + 48), f"last look (24) {gaze_text(cur)}", size=S.T_BODY, plate=S.WHITE)
        px_, py_ = ch.pt(prop)
        if k < 6:
            S.crosshair(d, px_, py_, r=22, solid=False)
            S.text(d, (px_ + 30, py_ - 60), f"proposal {gaze_text(prop)} (FSG6f, unchanged)", size=S.T_BODY, bold=True,
                   plate=S.WHITE)
        else:
            S.crosshair(d, px_, py_, r=22, solid=False, color=S.FAINT)
            d.line([px_ - 34, py_ - 34, px_ + 34, py_ + 34], fill=S.OI_VERM, width=7)
            d.line([px_ - 34, py_ + 34, px_ + 34, py_ - 34], fill=S.OI_VERM, width=7)
            S.text(d, (px_ + 40, py_ - 60), "proposal withdrawn: not executed", size=S.T_BODY, bold=True, plate=S.WHITE,
                   fill=S.OI_VERM)
            S.text(d, (16, ch.h - 70), "the unresolved support is still there (not claimed resolved)", size=S.T_BODY,
                   bold=True, plate=S.WHITE, fill=S.OI_VERM)
        canvas = event_canvas(ctx, "Strict final-look gate for 210 wall.008" if k < 6 else "REJECT: no novel serviceable support",
                              "would the unchanged local proposal place its own unresolved support inside both depth cores?",
                              "RESIDUE", "RESIDUE", {**states_after(ctx, ctx.n - 1)}, 210,
                              phase_cells={"RESIDUE": "current"}, timeline_current=ctx.n - 1)
        big_panel(canvas, (16, 92, 16 + 1604, 92 + 1100), "FINAL RESIDUE DECISION: 210 wall.008", ["DERIVED", "CONTROLLER-TIME"],
                  im.resize((1600, 1050)), tag="RESIDUE")
        right = Image.new("RGB", (V.W - 1650 - 20, 1050), S.PANEL)
        rows = [("unchanged FSG6f proposal", gaze_text(prop)), ("OPEN support elements", str(g["support"])),
                ("entering both predicted depth cores", str(g["in_both_cores"])),
                ("previously interrogated", str(g["previously_interrogated"])),
                ("novel_service_count", str(g["novel_service_count"]))]
        dr = ImageDraw.Draw(right)
        y = 30
        for n, (lab, val) in enumerate(rows):
            if n < k:
                dr.text((24, y), lab, font=S.font(S.T_BODY), fill=S.INK2)
                dr.text((24, y + 30), val, font=S.font(S.T_BIG + 6, True), fill=S.INK)
            y += 110
        if k == 6:
            dr.rectangle([24, y, 830, y + 120], fill=S.WHITE, outline=S.OI_VERM, width=6)
            dr.text((44, y + 10), "REJECT", font=S.font(S.T_HUGE, True), fill=S.OI_VERM)
            dr.text((44, y + 84), g["reason"], font=S.font(S.T_BODY, True), fill=S.OI_VERM)
            y += 150
            for lab in ("NO RENDER", "NO OBSERVE"):
                dr.rectangle([24, y, 400, y + 60], fill=S.INK)
                dr.text((44, y + 12), lab, font=S.font(S.T_HEAD + 4, True), fill=S.WHITE)
                y += 76
            dr.text((24, y + 6), f"final residue observations: {g['final_residue_observations']}", font=S.font(S.T_BODY, True),
                    fill=S.INK)
        big_panel(canvas, (1636, 92, V.W - 16, 92 + 1100), "GATE v1 LEDGER", ["CONTROLLER-TIME"], right)
        stages.append(canvas)
    meta = {"kind": "special", "event": "final_residue_gate_0210", "phase": "RESIDUE", **g, "stages": names,
            "window": list(win), "truth": ["CONTROLLER-TIME", "DERIVED"]}
    return stages, meta


# ---------------------------------------------------------------- honest closure

def closure_stages(ctx: Ctx):
    res = ctx.src.c02_result
    term = res["terminal"]
    fs = res["final_states"]
    quiet = sorted(term["quiet"])
    residual = term["residual"]
    unl = len(term["unlocated"])
    states = {int(k): ("RESIDUAL" if v["disposition"] == "FINALIZED" and v["local_state"] != "QUIET" else v["local_state"])
              for k, v in fs.items()}
    xyz, _rgb, ids = final_maps(ctx)
    ch = V.Chart(-25.0, 25.0, -20.0, 20.0, 1000 / 50.0)
    stages = []
    for k in (1, 2):
        canvas = event_canvas(ctx, "SCENE_CLOSED", "the scene finishes honestly: everything it will spend has been spent",
                              "CLOSED", "CLOSED", states, None, phase_cells={"RESIDUE": "done", "CLOSED": "current"},
                              timeline_current=ctx.n - 1)
        left = Image.new("RGB", (1300, 1050), S.PANEL)
        dl = ImageDraw.Draw(left)
        tile, gap = 116, 12
        for n, i in enumerate(sorted(states)):
            x0 = 30 + (n % 9) * (tile + gap)
            y0 = 30 + (n // 9) * (tile + 44)
            S.state_tile(left, (x0, y0, x0 + tile, y0 + tile - 30), states[i], str(i), size=S.T_HEAD)
            dl.text((x0, y0 + tile - 24), ctx.src.names(i)[:11], font=S.font(S.T_SMALL - 4), fill=S.INK2)
        S.state_tile(left, (30, 520, 330, 610), "UNLOCATED", f"{unl} unlocated", size=S.T_HEAD)
        rows = [f"quiet localized objects: {len(quiet)}",
                f"residual localized objects: {len(residual)}"]
        rows += [f"    {r_[0]} {ctx.src.names(r_[0])}: {r_[1]}, FINALIZED: {r_[2]}" for r_ in residual]
        rows += [f"unlocated: {unl}", f"final residue observations: {res['final_residue_observations']}"]
        V.plate_lines(left, (30, 650), [(rows[0], {"bold": True})] + rows[1:], size=S.T_HEAD, gap=12)
        big_panel(canvas, (16, 92, 16 + 1304, 92 + 1100), "FINAL OBJECT STATES", ["CONTROLLER-TIME"], left, tag="CLOSED")
        right = state_chart(ctx, ch, xyz, ids, residual=[r_[0] for r_ in residual],
                            labels=[(r_[0], f"{r_[0]} residual") for r_ in residual])
        rc = Image.new("RGB", (V.W - 1350 - 20, 1050), S.PANEL)
        rc.paste(right, ((rc.width - right.width) // 2, 0))
        if k == 2:
            dr = ImageDraw.Draw(rc)
            y = right.height + 40
            for s_ in ("residual ≠ failure", "SCENE_CLOSED ≠ global quiescence"):
                dr.rectangle([20, y, 1150, y + 84], fill=S.WHITE, outline=S.INK, width=4)
                dr.text((44, y + 16), s_, font=S.font(S.T_BIG + 4, True), fill=S.INK)
                y += 104
        big_panel(canvas, (1336, 92, V.W - 16, 92 + 1100), "WHAT REMAINS", ["CONTROLLER-TIME"], rc)
        stages.append(canvas)
    meta = {"kind": "special", "event": "closure", "phase": "CLOSED", "terminal": term["type"], "quiet": len(quiet),
            "residual": residual, "unlocated": unl, "final_residue_observations": res["final_residue_observations"],
            "truth": ["CONTROLLER-TIME"]}
    return stages, meta


# ---------------------------------------------------------------- legend, intro, guide

def legend_image() -> tuple[Image.Image, dict]:
    im = Image.new("RGB", (V.W, V.H), S.SURFACE)
    d = ImageDraw.Draw(im)
    d.text((40, 24), "VISUAL LANGUAGE 1", font=S.font(S.T_HUGE - 8, True), fill=S.INK)
    d.text((40, 92), "every role has a color and a non-color cue (shape, outline, hatch, dash or glyph)",
           font=S.font(S.T_BODY), fill=S.INK2)
    cols = [["TRUTH / PROVENANCE", "ATTENTION"], ["EPISTEMIC", "SENSOR"], ["MEASUREMENT / GEOMETRY", "SERVICE STATE"]]
    colw = (V.W - 80) // 3
    layout = []
    for c, groups in enumerate(cols):
        x = 40 + c * colw
        y = 160
        for g in groups:
            d.text((x, y), g, font=S.font(S.T_HEAD + 2, True), fill=S.INK)
            y += 50
            for r in S.ROLES:
                if r[0] != g:
                    continue
                key = r[1]
                if g == "TRUTH / PROVENANCE":
                    S.badge(im, x + 320, y, S.ROLE[key]["label"].split(":")[0], size=S.T_SMALL)
                    d = ImageDraw.Draw(im)
                    rest = textwrap.wrap(S.ROLE[key]["label"].split(": ", 1)[1], 38)
                    for n_, ln in enumerate(rest[:2]):
                        d.text((x + 334, y + 22 * n_), ln, font=S.font(S.T_SMALL - 3), fill=S.INK2)
                    y += 58
                else:
                    im.paste(S.swatch(key, 140, 50), (x, y))
                    d = ImageDraw.Draw(im)
                    d.text((x + 156, y - 2), S.ROLE[key]["label"], font=S.font(S.T_SMALL + 1, True), fill=S.INK)
                    d.text((x + 156, y + 26), S.ROLE[key]["cue"], font=S.font(S.T_SMALL - 3), fill=S.INK2)
                    y += 68
                layout.append(key)
            y += 20
    y = V.H - 118
    d.text((40, y), "SOURCES", font=S.font(S.T_BODY, True), fill=S.INK)
    x = 190
    for src, (lab, col, shape) in S.SOURCES.items():
        if shape == "square":
            d.rectangle([x, y + 4, x + 20, y + 24], fill=col)
        elif shape == "circle":
            d.ellipse([x, y + 4, x + 20, y + 24], fill=col)
        else:
            d.polygon([(x + 10, y + 1), (x + 21, y + 14), (x + 10, y + 27), (x - 1, y + 14)], fill=col)
        d.text((x + 30, y + 2), lab, font=S.font(S.T_BODY), fill=S.INK)
        x += 60 + d.textlength(lab, font=S.font(S.T_BODY))
    x += 40
    d.text((x, y + 2), "EVENTS", font=S.font(S.T_BODY, True), fill=S.INK)
    d.text((x + 120, y + 2), "✓ quiet    ▲ natural reactivation    ◆ + hatched band: deferred",
           font=S.font(S.T_BODY), fill=S.INK)
    y += 44
    d.text((40, y), "KEPT APART", font=S.font(S.T_BODY, True), fill=S.INK)
    d.text((220, y), "   ·   ".join(s.replace("!=", "≠") for s in S.DISTINCTIONS), font=S.font(S.T_SMALL, True),
           fill=S.INK)
    return im, {"roles": S.declaration(), "drawn_order": layout, "sources": {k: v[0] for k, v in S.SOURCES.items()},
                "distinctions": S.DISTINCTIONS}


def intro_stages(ctx: Ctx):
    im = Image.new("RGB", (V.W, V.H), S.WHITE)
    d = ImageDraw.Draw(im)
    d.text((160, 220), "FOVEAL STEREO VISION", font=S.font(96, True), fill=S.INK)
    d.text((164, 350), "Controller-02 · Classroom · the full canonical run (141 looks)", font=S.font(S.T_BIG), fill=S.INK2)
    d.rectangle([160, 450, 1500, 540], outline=S.INK, width=5)
    d.text((190, 468), "CONTROLLED PROOF OF CONCEPT", font=S.font(S.T_HUGE - 8, True), fill=S.INK)
    lines = [("current oracle boundary", {"bold": True, "size": S.T_HEAD}),
             ("• the Blender scene graph supplies the initial object catalog and one seed per localized object", {}),
             ("• current-pair Blender Position / Object Index passes support the controlled stereo / instance measurement", {}),
             ("• dense evaluation truth does NOT participate in controller decisions", {"bold": True}),
             ("", {"size": 20}),
             ("fixed head · two eyes rotate · a 12° binocular depth-measuring core inside a 29° view", {}),
             ("no new observation was made for this demo: it replays the accepted evidence", {"fill": S.INK2})]
    V.plate_lines(im, (164, 610), lines, size=S.T_HEAD - 2, gap=14)
    x = V.W - 180
    for b in ("CONTROLLER-TIME", "DERIVED", "ORACLE INPUT", "REFERENCE / EVALUATION"):
        x = S.badge(im, x, 1300, b, size=S.T_BODY) - 16
    d = ImageDraw.Draw(im)
    d.text((164, 1310), "truth badges used throughout:", font=S.font(S.T_BODY), fill=S.INK2)
    return [im], {"kind": "special", "event": "intro", "truth": ["CONTROLLER-TIME"], "phase": "-"}


def guide_stage(step_png: Path) -> tuple[Image.Image, dict]:
    base = Image.open(step_png).convert("RGB")
    im = Image.fromarray(lighten(np.asarray(base), 0.55))
    d = ImageDraw.Draw(im)
    notes = [(0, "BEFORE the look", ["where attention is (solid crosshair)", "and where it goes next (dashed)"]),
             (1, "the OBSERVATION", ["what the two eyes saw;", "where depth was actually measured"]),
             (2, "AFTER the look", ["what the system knows about the target", "and what is still unresolved (rings)"]),
             (3, "AFTER the look", ["what persistent 3-D geometry changed:", "new surfels vs repeated measurements"])]
    for idx, head, body in notes:
        x, y = V.PANEL_XY[idx]
        box = [x + 180, y + 150, x + 1080, y + 390]
        d.rectangle(box, fill=S.WHITE, outline=S.INK, width=5)
        d.text((box[0] + 30, box[1] + 22), f"{idx + 1}  {head}", font=S.font(S.T_BIG, True), fill=S.INK)
        for n, ln in enumerate(body):
            d.text((box[0] + 30, box[1] + 90 + n * 44), ln, font=S.font(S.T_HEAD + 4), fill=S.INK)
    d.rectangle([700, V.ROSTER_Y - 6, 1860, V.ROSTER_Y + 60], fill=S.WHITE, outline=S.INK, width=4)
    d.text((720, V.ROSTER_Y + 6), "every object's service state · below: the 141-look timeline",
           font=S.font(S.T_HEAD, True), fill=S.INK)
    d.rectangle([640, 14, 1900, 74], fill=S.WHITE, outline=S.INK, width=4)
    d.text((660, 24), "HOW TO READ THE COCKPIT (one frame per look)", font=S.font(S.T_TITLE, True), fill=S.INK)
    return im, {"kind": "special", "event": "guide", "truth": ["CONTROLLER-TIME", "DERIVED", "ORACLE INPUT"], "phase": "-"}


# ---------------------------------------------------------------- outro, panoramas, point clouds

def memory_by_step(ctx: Ctx):
    mem = Memory(ctx)
    mem.advance(ctx.n - 1)
    xyz = np.concatenate(mem.xyz); rgb = np.concatenate(mem.rgb); inst = np.concatenate(mem.inst)
    step = np.concatenate([np.full(len(x), s, np.int16) for s, x in enumerate(mem.xyz)])
    return xyz, rgb, inst, step


def outro_stages(ctx: Ctx, mxyz, mstep):
    xyz, rgb, ids = final_maps(ctx)
    ch = V.Chart(-25.0, 25.0, -20.0, 20.0, 1240 / 50.0)
    stages = []
    # 1: final active fused scene (chart + 3-D)
    canvas = Image.new("RGB", (V.W, V.H), S.SURFACE)
    V.header(canvas, "Final active fused scene", f"25 objects · {fmt(len(xyz))} surfels · surfel color",
             "CLOSED", "OUTRO")
    a = Image.fromarray(V.splat(ch, xyz, rgb, radius=1))
    big_panel(canvas, (16, 92, 1276, 92 + 1060), "HEAD-CENTRED VIEW", ["CONTROLLER-TIME"], a)
    view = V.View3D(ctx.cam, (1240, 1000))
    b = Image.fromarray(view.render(xyz, rgb))
    V.head_glyph(b, view)
    big_panel(canvas, (1292, 92, V.W - 16, 92 + 1060), "STANDARD 3-D CAMERA (above and behind the head)", ["CONTROLLER-TIME"], b)
    stages.append(canvas)
    # 2: causal measurement memory colored by look
    canvas = Image.new("RGB", (V.W, V.H), S.SURFACE)
    V.header(canvas, "Causal measurement memory", f"every valid measurement of the 141 looks: {fmt(len(mxyz))} points, "
             "colored by the look that made it", "CLOSED", "OUTRO")
    t = (mstep.astype(np.float32) / (ctx.n - 1))[:, None]
    lo, hi = np.array([214, 229, 247]), np.array([8, 48, 107])
    cols = (lo * (1 - t) + hi * t).astype(np.uint8)
    a = Image.fromarray(V.splat(ch, mxyz, cols, radius=0))
    big_panel(canvas, (16, 92, 1276, 92 + 1060), "HEAD-CENTRED VIEW (light = early, dark = late)", ["CONTROLLER-TIME"], a)
    b = Image.fromarray(view.render(mxyz, cols))
    V.head_glyph(b, view)
    big_panel(canvas, (1292, 92, V.W - 16, 92 + 1060), "STANDARD 3-D CAMERA", ["CONTROLLER-TIME"], b)
    stages.append(canvas)
    return stages, {"kind": "special", "event": "outro", "active_map_surfels": int(len(xyz)),
                    "measurement_points": int(len(mxyz)), "truth": ["CONTROLLER-TIME"], "phase": "CLOSED"}


def panorama_footprint(ctx: Ctx) -> tuple[Image.Image, dict]:
    z = D.load_npz(ctx.cache / "final/footprint.npz")
    seen, depth = z["seen_any"].astype(bool), z["depth_seen"].astype(bool)
    ch = V.Chart(-25.0, 25.0, -20.0, 20.0, 40.0)
    sc = V.cells(ch, seen.astype(np.int32)); dc = V.cells(ch, depth.astype(np.int32))
    img = np.full((ch.h, ch.w, 3), S.UNKNOWN_BG, np.uint8)
    img[sc == 1] = (214, 230, 222)
    img[dc == 1] = (120, 170, 150)
    im = Image.fromarray(img)
    V.grid_lines(im, ch, labels=True)
    d = ImageDraw.Draw(im)
    for a in ctx.actions:
        x, y = ch.pt(a["gaze_deg"])
        _l, col, shape = S.SOURCES[a["action_source"]]
        r = 7
        if shape == "square":
            d.rectangle([x - r, y - r, x + r, y + r], fill=col, outline=S.WHITE)
        elif shape == "circle":
            d.ellipse([x - r, y - r, x + r, y + r], fill=col, outline=S.WHITE)
        else:
            d.polygon([(x, y - r - 2), (x + r + 2, y), (x, y + r + 2), (x - r - 2, y)], fill=col, outline=S.WHITE)
    out = Image.new("RGB", (ch.w + 40, ch.h + 190), S.SURFACE)
    out.paste(im, (20, 150))
    do = ImageDraw.Draw(out)
    do.text((20, 16), "Observed footprint after 141 looks: visible ≠ depth measured", font=S.font(S.T_TITLE, True), fill=S.INK)
    n_seen, n_depth = int(seen.sum()), int(depth.sum())
    do.rectangle([20, 70, 50, 96], fill=(214, 230, 222)); do.text((60, 70), f"seen by an eye ray: {fmt(n_seen)} cells (0.1°)",
                                                                   font=S.font(S.T_BODY), fill=S.INK)
    do.rectangle([720, 70, 750, 96], fill=(120, 170, 150)); do.text((760, 70), f"depth measured (head chart): {fmt(n_depth)} cells",
                                                                     font=S.font(S.T_BODY), fill=S.INK)
    do.text((20, 108), "marks: the 141 fixations (square seed, circle FSG6f, diamond Cyclopean)", font=S.font(S.T_SMALL),
            fill=S.INK2)
    S.badge(out, out.width - 20, 16, "CONTROLLER-TIME")
    return out, {"seen_cells": n_seen, "depth_cells": n_depth, "fixations": len(ctx.actions)}


def panorama_final_210(ctx: Ctx) -> tuple[Image.Image, dict]:
    stages, meta = gate_stages(ctx)
    return stages[-1], {k: meta[k] for k in ("support", "in_both_cores", "previously_interrogated", "novel_service_count",
                                              "reason", "admissible")}


def write_ply(path: Path, xyz, rgb, extra: dict, comment: str) -> str:
    n = len(xyz)
    fields = [("x", "<f4"), ("y", "<f4"), ("z", "<f4"), ("red", "u1"), ("green", "u1"), ("blue", "u1")]
    fields += [(k, v.dtype.str) for k, v in extra.items()]
    arr = np.empty(n, dtype=fields)
    arr["x"], arr["y"], arr["z"] = xyz[:, 0], xyz[:, 1], xyz[:, 2]
    arr["red"], arr["green"], arr["blue"] = rgb[:, 0], rgb[:, 1], rgb[:, 2]
    for k, v in extra.items():
        arr[k] = v
    ply_t = {"<f4": "float", "u1": "uchar", "<i4": "int", "<i2": "short"}
    head = "ply\nformat binary_little_endian 1.0\n" + f"comment {comment}\n" + f"element vertex {n}\n"
    head += "".join(f"property {ply_t[v]} {k}\n" for k, v in fields) + "end_header\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(head.encode() + arr.tobytes())
    return D.sha(path)


# ---------------------------------------------------------------- overview poster and narration

def overview_poster(ctx: Ctx, thumbs: dict, numbers: dict) -> Image.Image:
    Wp, Hp = 3200, 1860
    im = Image.new("RGB", (Wp, Hp), S.SURFACE)
    d = ImageDraw.Draw(im)
    d.text((50, 30), "Controller-02 · Classroom: from bootstrap to an honest SCENE_CLOSED", font=S.font(56, True), fill=S.INK)
    d.rectangle([50, 108, 700, 150], outline=S.INK, width=3)
    d.text((64, 114), "CONTROLLED PROOF OF CONCEPT", font=S.font(S.T_HEAD, True), fill=S.INK)
    d.text((730, 116), "oracle catalog / seeds and current-pair oracle stereo · no evaluation truth in control · "
                        "141 accepted looks replayed, no new observation", font=S.font(S.T_BODY), fill=S.INK2)
    cards = [
        ("1  BOOTSTRAP", "bootstrap", ["ORACLE INPUT"],
         [f"{numbers['catalog']} catalog objects → {numbers['localized']} localized", "one seed gaze each",
          f"{numbers['unlocated']} unlocated (never targets)"]),
        ("2  NORMAL ACTIVE PERCEPTION", "normal", ["CONTROLLER-TIME"],
         [f"{numbers['looks']} looks: {numbers['sources']['oracle_seed']} seed, {numbers['sources']['fsg6f']} FSG6f, "
          f"{numbers['sources']['cyclopean_epistemic']} Cyclopean", f"{numbers['switches']} attention switches",
          f"new surfels {fmt(numbers['new_surfels'])} · repeated {fmt(numbers['repeated'])}"]),
        ("3  NATURAL REACTIVATION", "reactivation", ["CONTROLLER-TIME", "DERIVED"],
         [f"178: QUIET (67) → {fmt(numbers['r178']['added'])} cross-target points",
          f"eligible {numbers['r178']['eligible'][0]} → {numbers['r178']['eligible'][1]} → ACTIONABLE → serviced ({numbers['r178']['served']})",
          f"109: {numbers['r109']['added']} points, eligible {numbers['r109']['eligible'][0]} → {numbers['r109']['eligible'][1]}"]),
        ("4  DEFERRAL", "defer", ["CONTROLLER-TIME"],
         [f"210 at look {numbers['defer']['global_step']}: {numbers['defer']['fixations']} looks = budget",
          "local ACTIONABLE → DEFERRED", "DEFERRED ≠ QUIET; the scene keeps going"]),
        ("5  FINAL RESIDUE GATE", "gate", ["DERIVED", "CONTROLLER-TIME"],
         [f"unchanged FSG6f {gaze_text(numbers['gate']['gaze'])}: {numbers['gate']['support']} OPEN support",
          f"in both predicted cores {numbers['gate']['in_both_cores']} · previously {numbers['gate']['previously_interrogated']}",
          f"novel {numbers['gate']['novel_service_count']} → REJECT · no render, no observe"]),
        ("6  SCENE_CLOSED", "closure", ["CONTROLLER-TIME"],
         [f"{numbers['closure']['quiet']} QUIET · residual 210 (ACTIONABLE)",
          f"{numbers['closure']['unlocated']} unlocated · final looks {numbers['closure']['final_residue_observations']}",
          "residual ≠ failure · SCENE_CLOSED ≠ global quiescence"]),
    ]
    tw, th = 960, 540
    for n, (head, key, badges, lines) in enumerate(cards):
        cx = 50 + (n % 3) * (tw + 100)
        cy = 190 + (n // 3) * (th + 300)
        d.rectangle([cx - 4, cy - 4, cx + tw + 4, cy + th + 244], fill=S.WHITE, outline=(205, 204, 199), width=2)
        im.paste(thumbs[key].resize((tw, th), Image.LANCZOS), (cx, cy))
        d = ImageDraw.Draw(im)
        d.text((cx + 10, cy + th + 12), head, font=S.font(S.T_TITLE + 4, True), fill=S.INK)
        bx = cx + tw - 6
        for b in reversed(badges):
            bx = S.badge(im, bx, cy + th + 14, b, size=S.T_SMALL - 2) - 6
        d = ImageDraw.Draw(im)
        for k, ln in enumerate(lines):
            d.text((cx + 10, cy + th + 64 + k * 40), ln, font=S.font(S.T_HEAD), fill=S.INK)
        if n % 3 != 2:
            S.arrow(d, cx + tw + 16, cy + th / 2, cx + tw + 84, cy + th / 2, width=6, head=26)
    d.text((50, Hp - 56), "   ·   ".join(s.replace("!=", "≠") for s in S.DISTINCTIONS), font=S.font(S.T_HEAD, True),
           fill=S.INK)
    return im


NARRATION = """# Controller-02 Classroom: narration (Visual Language 1)

A concise voice-over for the canonical demo. Times refer to
`demo/controller-02-classroom-full-1440p.mp4`; the exact segment times are in
`demo/logical-frame-manifest.json`.

## Intro ({intro})
This is foveal stereo vision on a fixed head, in the Classroom scene. It is a controlled proof of concept.
The Blender scene graph gives the initial object catalog and one seed per localized object. The current
image pair's oracle position and object-index passes support stereo and instance measurement. Dense
evaluation truth never takes part in a controller decision. Nothing new was observed for this video; it
replays the accepted run.

## Visual language and the cockpit ({legend})
Every role has a color and a second cue: a shape, outline, hatch, dash or glyph. Each look is one
frame of a four-panel cockpit:
- top left, the scene before the look (solid crosshair: where the eyes are; dashed: where they go);
- top right, what the two eyes saw, and where depth was actually measured;
- bottom left, what the system knows about its target after the look, and what is still unresolved;
- bottom right, what the look changed in persistent 3-D memory.

## Bootstrap ({bootstrap})
Of {catalog} catalog objects, {localized} are visible inside the controller's domain. Each gets one seed direction.
The other {unlocated} are never localized and never become targets.

## The ordinary loop ({loop})
The controller looks at one object at a time. The accepted local policy proposes each next look, from the
FSG6f frontier or, when that has nothing, from the Cyclopean epistemic chart. A green square is new surface;
a purple ring is a measurement that repeats geometry already known. Most looks measure far more than
they add.

## Natural reactivation of 109 ({r109})
109 was quiet. A look at the beams measured four of its points by accident. They are shown magnified.
Those four points opened 28 eligible cells in its Cyclopean chart, so 109 became actionable again without
a look of its own. It was serviced at look 134.

## Deferral of 210 ({defer})
After 24 looks, the wall 210 still wants another look. Instead of blocking it, Controller-02 defers it.
Deferred is not quiet. The rest of the scene keeps receiving service.

## Natural reactivation of 178 ({r178})
The floor, 178, was quiet. Looks at 201 and 224 measured 36,748 of its points. Its eligible cells went from 0
to 189, and it became actionable again. It was serviced at look 136.

## Residue gate ({gate})
Ordinary work is exhausted: 24 objects are quiet and one is deferred. For 210, the unchanged local
proposal is tested once, without rendering. Its 30 unresolved support elements would enter both predicted
depth cores zero times, and all 30 were already interrogated binocularly. Novel service would be zero, so
the final look is rejected. There is no render and no observation, and the unresolved support stays on
screen.

## Scene closure ({closure})
The scene closes with 24 quiet objects and one explicit residual, 210, still locally actionable. 209
objects stay unlocated, and no final look was executed. A residual is not a failure, and a closed scene is not
global quiescence.

## Outro ({outro})
The final fused maps, the causal measurement memory colored by look, and, in a separate labelled
panel, a reference view that the controller never used.
"""


# ---------------------------------------------------------------- render driver

_WCTX: Ctx | None = None


def _worker_init(source, replay, cache):
    global _WCTX
    fw = D.firewall()
    with fw:
        _WCTX = Ctx(source, replay, cache)


def _render_chunk(args):
    steps, out = args
    fw = D.firewall()
    metas = []
    with fw:
        mem = Memory(_WCTX)
        for t in steps:
            img, meta = step_frame(_WCTX, mem, t)
            img.save(Path(out) / f"frames/step_{t:03d}.png", optimize=False)
            metas.append(meta)
    return metas, sorted(fw.opened), list(fw.violations)


def save_stages(stages, cache: Path, name: str) -> list[str]:
    paths = []
    d = cache / "video-stages"
    d.mkdir(parents=True, exist_ok=True)
    for k, im in enumerate(stages):
        p = d / f"{name}_{k}.png"
        im.save(p)
        paths.append(str(p))
    return paths


def render(source: Path, replay: Path, cache: Path, out: Path, workers: int = 16, log=print) -> dict:
    source, replay, cache, out = (Path(p).resolve() for p in (source, replay, cache, out))
    t0 = time.perf_counter()
    for sub in ("frames", "events", "legend", "panoramas", "pointclouds", "demo"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    fw = D.firewall()
    with fw:
        src = D.Sources(source, replay)
        checks = D.verify_sources(src)
        cam = prepare_camera(src, cache)
    opened = set(fw.opened)
    violations = list(fw.violations)
    n = len(src.actions)
    chunks = [list(range(int(k * n / workers), int((k + 1) * n / workers))) for k in range(workers)]
    with mp.get_context("fork").Pool(workers, initializer=_worker_init, initargs=(source, replay, cache)) as pool:
        results = pool.map(_render_chunk, [(c, out) for c in chunks if c])
    step_meta = {}
    for metas, op, vi in results:
        opened |= set(op)
        violations += vi
        for m in metas:
            step_meta[m["global_step"]] = m
    log(f"[vl1-render] {len(step_meta)} step frames ({time.perf_counter() - t0:.0f} s)")
    fw = D.firewall()
    with fw:
        ctx = Ctx(source, replay, cache)
        specials = {}
        for name, fn, final in (("bootstrap", lambda: bootstrap_stages(ctx), "frames/bootstrap.png"),
                                ("event_reactivation_0109", lambda: reactivation_stages(ctx, 109), "events/reactivation-0109.png"),
                                ("event_defer_0210", lambda: defer_stages(ctx), "events/defer-0210.png"),
                                ("event_reactivation_0178", lambda: reactivation_stages(ctx, 178), "events/reactivation-0178.png"),
                                ("residue", lambda: residue_stages(ctx), "frames/residue.png"),
                                ("event_final_residue_gate_0210", lambda: gate_stages(ctx), "events/final-residue-gate-0210.png"),
                                ("closure", lambda: closure_stages(ctx), "frames/closure.png"),
                                ("intro", lambda: intro_stages(ctx), None)):
            stages, meta = fn()
            if final:
                stages[-1].save(out / final)
            specials[name] = {**meta, "stages": save_stages(stages, cache, name), "package_file": final}
        leg, leg_meta = legend_image()
        leg.save(out / "legend/visual-language-1.png")
        D.write_json(out / "legend/visual-language-1.json", leg_meta)
        specials["legend"] = {"kind": "special", "event": "legend", "truth": [], "phase": "-",
                              "stages": save_stages([leg], cache, "legend"), "package_file": "legend/visual-language-1.png"}
        gimg, gmeta = guide_stage(out / "frames/step_025.png")
        specials["guide"] = {**gmeta, "stages": save_stages([gimg], cache, "guide"), "package_file": None,
                             "based_on": "frames/step_025.png"}
        mxyz, mrgb, minst, mstep = memory_by_step(ctx)
        ostages, ometa = outro_stages(ctx, mxyz, mstep)
        specials["outro"] = {**ometa, "stages": save_stages(ostages, cache, "outro"), "package_file": None}
        fp, fp_meta = panorama_footprint(ctx)
        fp.save(out / "panoramas/observed-footprint.png")
        p210, p210_meta = panorama_final_210(ctx)
        p210.save(out / "panoramas/final-epistemic-0210.png")
        # point clouds (full data)
        xyz, rgb, ids = final_maps(ctx)
        ply = {"scene-active-maps.ply": {"points": int(len(xyz)), "sha256": write_ply(
            out / "pointclouds/scene-active-maps.ply", xyz, rgb, {"instance": ids.astype("<i4")},
            "Controller-01/02 Classroom final active fused maps (25 objects); fixed head frame x right y up -z forward; metres"),
            "source": "objects/instance_*/final_map.npz (manifest object order); rgb = gamma(surfel rgb)"},
            "scene-measurement-memory.ply": {"points": int(len(mxyz)), "sha256": write_ply(
                out / "pointclouds/scene-measurement-memory.ply", mxyz, mrgb,
                {"instance": minst.astype("<i4"), "step": mstep.astype("<i2")},
                "Controller-01/02 Classroom causal measurement memory: every valid measurement of the 141 looks; look RGB"),
                "source": "objects/instance_*/patches/fix_*.npz valid & instance > 0, in action order; rgb = benchmark left PNG"}}
        # overview
        acts = ctx.actions
        srcs = {k: sum(1 for a in acts if a["action_source"] == k) for k in S.SOURCES}
        switches = sum(1 for a, b in zip(acts[:-1], acts[1:]) if a["target_id"] != b["target_id"])
        numbers = {"catalog": specials["bootstrap"]["catalog"], "localized": specials["bootstrap"]["localized"],
                   "unlocated": specials["bootstrap"]["unlocated"], "looks": len(acts), "sources": srcs, "switches": switches,
                   "new_surfels": sum(s["new_surfels"] for s in ctx.steps),
                   "repeated": sum(s["repeated_measurements"] for s in ctx.steps),
                   "r109": {k: specials["event_reactivation_0109"][k] for k in ("added", "eligible", "served")},
                   "r178": {k: specials["event_reactivation_0178"][k] for k in ("added", "eligible", "served")},
                   "defer": {k: specials["event_defer_0210"][k] for k in ("global_step", "fixations", "local_state")},
                   "gate": {k: specials["event_final_residue_gate_0210"][k] for k in
                            ("gaze", "support", "in_both_cores", "previously_interrogated", "novel_service_count", "reason",
                             "admissible")},
                   "closure": {k: specials["closure"][k] for k in ("terminal", "quiet", "residual", "unlocated",
                                                                    "final_residue_observations")}}
        thumbs = {"bootstrap": Image.open(out / "frames/bootstrap.png"), "normal": Image.open(out / "frames/step_060.png"),
                  "reactivation": Image.open(out / "events/reactivation-0178.png"), "defer": Image.open(out / "events/defer-0210.png"),
                  "gate": Image.open(out / "events/final-residue-gate-0210.png"), "closure": Image.open(out / "frames/closure.png")}
        overview_poster(ctx, thumbs, numbers).save(out / "overview.png")
        D.write_json(out / "overview.json", {"numbers": numbers, "thumbnails": {
            "bootstrap": "frames/bootstrap.png", "normal": "frames/step_060.png", "reactivation": "events/reactivation-0178.png",
            "defer": "events/defer-0210.png", "gate": "events/final-residue-gate-0210.png", "closure": "frames/closure.png"}})
    opened |= set(fw.opened)
    violations += fw.violations
    manifest = {"schema": "VisualLanguage1-render-v1", "contract": "docs/methodology/visual-language-1-contract.md",
                "path": "controller-time rendering (truth firewall: no evaluation truth, no reference product)",
                "source_checks": checks, "camera": cam, "steps": [step_meta[t] for t in range(n)], "specials": specials,
                "panoramas": {"observed-footprint.png": fp_meta, "final-epistemic-0210.png": p210_meta},
                "pointclouds": ply, "overview_numbers": numbers,
                "opened_source_files": sorted(opened), "firewall_violations": violations,
                "fonts": S.font_hashes(), "seconds": round(time.perf_counter() - t0, 1)}
    D.write_json(cache / "render-manifest.json", manifest)
    log(f"[vl1-render] done: {n} steps, {len(specials)} special frames; opened {len(opened)} files; "
        f"violations {len(violations)}; {manifest['seconds']} s")
    return manifest


# ---------------------------------------------------------------- the reference path (separate process)

def id_palette(ids: np.ndarray) -> np.ndarray:
    """A deterministic categorical coloring of instance ids (reference imagery only)."""
    h = (ids.astype(np.int64) * 2654435761) & 0xFFFFFFFF
    rgb = np.stack([(h >> 8) & 255, (h >> 16) & 255, (h >> 24) & 255], -1).astype(np.float32)
    rgb = 60 + rgb * (170 / 255)
    rgb[ids == 0] = 245
    return rgb.astype(np.uint8)


def reference(source: Path, cache: Path, out: Path, log=print) -> dict:
    """REFERENCE / EVALUATION products from the one reference render (never a controller-time input)."""
    source, cache, out = Path(source).resolve(), Path(cache).resolve(), Path(out).resolve()
    rdir = cache / "reference-render"
    refdir = cache / "reference"
    refdir.mkdir(parents=True, exist_ok=True)
    (out / "reference").mkdir(parents=True, exist_ok=True)
    fw = ic_firewall_reference()
    with fw:
        meta = json.loads((rdir / "reference.json").read_text())
        z = D.load_npz(rdir / "reference.npz")
        seeds = json.loads((source / "bootstrap/seeds.json").read_text())
        catalog = {int(o["instance_id"]): o["object_name"]
                   for o in json.loads((source / "bootstrap/instance_catalog.json").read_text())["instances"]}
        samples = D.load_npz(source / "bootstrap/evaluation_only/reachable_samples.npz")
        f, (cx, cy) = float(meta["f_px"]), meta["c_px"]
        ch = V.Chart(-25.0, 25.0, -20.0, 20.0, 40.0)

        def sample_dirs(yaw, pit):
            y, p = np.radians(yaw), np.radians(pit)
            dx, dy, dz = np.sin(y) * np.cos(p), np.sin(p), -np.cos(y) * np.cos(p)
            return cx + f * dx / -dz, cy - f * dy / -dz
        yy, xx = np.mgrid[0:ch.h, 0:ch.w]
        u, v = sample_dirs(ch.y0 + (xx + 0.5) / ch.s, ch.p1 - (yy + 0.5) / ch.s)
        rgb = cv2.remap(np.ascontiguousarray(z["rgb"]), u.astype(np.float32), v.astype(np.float32), cv2.INTER_LINEAR)
        ui, vi = np.clip(np.rint(u).astype(int), 0, z["instance"].shape[1] - 1), np.clip(np.rint(v).astype(int), 0, z["instance"].shape[0] - 1)
        inst = z["instance"][vi, ui]
        pos = z["position_w"][vi, ui]
        rng = np.linalg.norm(pos - np.asarray(seeds["head_origin_w_m"], float), axis=-1)
        rng[inst == 0] = np.nan
        # alignment against the existing evaluation-only dense samples (instance agreement, range)
        su, sv = sample_dirs(samples["yaw_pitch_deg"][:, 0], samples["yaw_pitch_deg"][:, 1])
        sui, svi = np.rint(su).astype(int), np.rint(sv).astype(int)
        inside = (sui >= 0) & (sui < z["instance"].shape[1]) & (svi >= 0) & (svi < z["instance"].shape[0])
        got = z["instance"][svi[inside], sui[inside]]
        agree = float(np.mean(got == samples["instance_id"][inside]))
        srng = np.linalg.norm(samples["xyz_h"][inside], axis=1)
        prng = np.linalg.norm(z["position_w"][svi[inside], sui[inside]] - np.asarray(seeds["head_origin_w_m"]), axis=1)
        close = float(np.mean(np.abs(prng - srng) < 0.02))
        names_ok = all(catalog.get(int(k)) == nm for k, nm in meta["instance_names"].items()) and \
            len(meta["instance_names"]) == len(catalog)
        aligned = agree >= 0.97 and close >= 0.95 and names_ok and bool(inside.all())
        log(f"[vl1-reference] alignment: instance agreement {agree:.4f}, range within 2 cm {close:.4f}, "
            f"ids = catalog {names_ok}, samples inside {int(inside.sum())}/{len(inside)} -> {'ALIGNED' if aligned else 'NOT ALIGNED'}")
        products = {}
        stages = {}
        if aligned:
            def framed(img, title, lines):
                canvas = Image.new("RGB", (img.width + 40, img.height + 150), S.SURFACE)
                canvas.paste(img, (20, 130))
                d = ImageDraw.Draw(canvas)
                d.text((20, 14), title, font=S.font(S.T_TITLE, True), fill=S.INK)
                for k, ln in enumerate(lines):
                    d.text((20, 56 + k * 30), ln, font=S.font(S.T_BODY), fill=S.INK2)
                S.badge(canvas, canvas.width - 20, 14, "REFERENCE / EVALUATION")
                return canvas
            srgb = Image.fromarray(D.gamma_u8(rgb))
            framed(srgb, "Scene reference: the Classroom from the fixed head (head-centred chart)",
                   ["one static Blender render; not an observation; never fed to the controller",
                    f"yaw -25..25, pitch -20..20 deg; {meta['spp']} spp; alignment checked: instance agreement {agree:.3f}"]
                   ).save(out / "reference/scene-reference.png")
            lo, hi = np.nanpercentile(rng, 1), np.nanpercentile(rng, 99)
            t = np.clip((np.nan_to_num(rng, nan=hi) - lo) / (hi - lo), 0, 1)[..., None]
            dimg = (np.array([214, 229, 247]) * (1 - t) + np.array([8, 48, 107]) * t).astype(np.uint8)
            dimg[np.isnan(rng)] = (245, 245, 243)
            framed(Image.fromarray(dimg), "Depth reference (range from the head origin)",
                   [f"from the same reference render's Position pass; near light ({lo:.2f} m) -> far dark ({hi:.2f} m)",
                    "reference / evaluation only"]).save(out / "reference/depth-reference.png")
            iimg = Image.fromarray(id_palette(inst))
            di = ImageDraw.Draw(iimg)
            for i, g in seeds and [(int(s["instance_id"]), s["seed_gaze_deg"]) for s in seeds["instances"]]:
                x, y = ch.pt(g)
                S.text(di, (x, y), f"{i}", size=S.T_SMALL, bold=True, plate=S.WHITE, anchor="mm")
            framed(iimg, "Instance reference (Object Index pass)",
                   ["same ids as the controller-time oracle instance channel; labels at the 25 seed directions",
                    "reference / evaluation only"]).save(out / "reference/instance-reference.png")
            for name in ("scene-reference.png", "depth-reference.png", "instance-reference.png"):
                products[name] = D.sha(out / "reference" / name)
            # video stages: intro hero, outro comparison (both explicitly labelled)
            hero = Image.new("RGB", (V.W, V.H), S.SURFACE)
            hero.paste(srgb.resize((1600, 1280), Image.LANCZOS), (80, 120))
            d = ImageDraw.Draw(hero)
            d.text((80, 30), "The scene (REFERENCE / EVALUATION view)", font=S.font(S.T_TITLE + 6, True), fill=S.INK)
            S.badge(hero, V.W - 40, 36, "REFERENCE / EVALUATION", size=S.T_BODY)
            V.plate_lines(hero, (1740, 160), [
                ("what a camera at the head would see", {"bold": True}), ("", {"size": 10}),
                ("one static Blender render,", {}), ("made only for this presentation", {}), ("", {"size": 10}),
                ("NOT an observation", {"bold": True}), ("NEVER fed to the controller", {"bold": True}),
                ("NOT part of any measurement", {"bold": True}), ("", {"size": 10}),
                ("same head-centred chart as the", {}), ("controller's panels:", {}), ("yaw ±25°, pitch ±20°", {}),
            ], size=S.T_HEAD, gap=8)
            p = refdir / "intro_reference_0.png"
            hero.save(p)
            stages["intro_reference"] = [str(p)]
            xyz = np.concatenate([np.asarray(D.load_npz(source / f"objects/instance_{int(o['instance_id']):04d}/final_map.npz")["xyz_h"])
                                  for o in json.loads((source / "manifest.json").read_text())["objects"]])
            cols = np.concatenate([D.gamma_u8(D.load_npz(source / f"objects/instance_{int(o['instance_id']):04d}/final_map.npz")["rgb"])
                                   for o in json.loads((source / "manifest.json").read_text())["objects"]])
            ch2 = V.Chart(-25.0, 25.0, -20.0, 20.0, 1220 / 50.0)
            amap = Image.fromarray(V.splat(ch2, xyz, cols, radius=1))
            comp = Image.new("RGB", (V.W, V.H), S.SURFACE)
            V.header(comp, "What was reconstructed vs the reference", "left: controller-time active fused maps · "
                     "right: the reference render (never used by the controller)", "CLOSED", "OUTRO")
            big_panel(comp, (16, 120, 1276, 120 + 1100), "ACTIVE FUSED MAPS (25 objects)", ["CONTROLLER-TIME"], amap)
            big_panel(comp, (1292, 120, V.W - 16, 120 + 1100), "SCENE REFERENCE", ["REFERENCE / EVALUATION"],
                      srgb.resize((1220, 976), Image.LANCZOS))
            p = refdir / "outro_reference_0.png"
            comp.save(p)
            stages["outro_reference"] = [str(p)]
    manifest = {"schema": "VisualLanguage1-reference-v1", "path": "REFERENCE / EVALUATION (separate process)",
                "render": {k: meta[k] for k in ("device", "spp", "seconds", "image_size_wh", "f_px", "blend")},
                "alignment": {"instance_agreement": agree, "range_within_2cm": close, "ids_equal_catalog": names_ok,
                              "samples": int(len(inside)), "aligned": aligned},
                "products": products, "stages": stages, "omitted_reason": None if aligned else "alignment check failed",
                "opened_files": sorted(fw.opened)}
    D.write_json(refdir / "reference-manifest.json", manifest)
    return manifest


def ic_firewall_reference():
    """The reference path may read reference/evaluation assets; it records what it opens."""
    return D.ic.TruthFirewall(D.PREVIEWS, lambda p: False)


# ---------------------------------------------------------------- video assembly and manifests

def sequence(render_m: dict, ref_m: dict | None) -> list[dict]:
    sp = render_m["specials"]
    holds = {"intro": [150], "intro_reference": [150], "legend": [300], "guide": [210], "bootstrap": [90, 150],
             "event_reactivation_0109": [90, 90, 90, 150], "event_defer_0210": [90, 90, 90, 150],
             "event_reactivation_0178": [90, 90, 90, 150], "residue": [90, 120],
             "event_final_residue_gate_0210": [90, 90, 105, 90, 90, 180], "closure": [120, 180], "outro": [150, 150],
             "outro_reference": [180]}
    order = ["intro"] + (["intro_reference"] if ref_m and ref_m["stages"].get("intro_reference") else []) + \
        ["legend", "guide", "bootstrap"]
    steps = {m["global_step"]: m for m in render_m["steps"]}
    after = {7: "event_reactivation_0109", 101: "event_defer_0210", 114: "event_reactivation_0178"}
    for t in range(len(steps)):
        order.append(("step", t))
        if t in after:
            order.append(after[t])
    order += ["residue", "event_final_residue_gate_0210", "closure", "outro"]
    if ref_m and ref_m["stages"].get("outro_reference"):
        order.append("outro_reference")
    frames, cur = [], 0
    for item in order:
        if isinstance(item, tuple):
            m = steps[item[1]]
            st = [{"image": f"frames/step_{item[1]:03d}.png", "frames": m["hold_frames"]}]
            entry = {"id": f"step_{item[1]:03d}", **{k: m[k] for k in m if k != "panels"}, "panels": m["panels"]}
        else:
            if item in ("intro_reference", "outro_reference"):
                imgs = ref_m["stages"][item]
                entry = {"id": item, "kind": "reference", "event": item, "truth": ["REFERENCE / EVALUATION"] +
                         (["CONTROLLER-TIME"] if item == "outro_reference" else []), "phase": "-"}
            else:
                imgs = sp[item]["stages"]
                entry = {"id": item, **{k: v for k, v in sp[item].items() if k != "stages"}}
            st = [{"image": p, "frames": h} for p, h in zip(imgs, holds[item])]
            if len(imgs) != len(holds[item]):
                raise RuntimeError(f"{item}: {len(imgs)} stages vs {len(holds[item])} holds")
        n = sum(s["frames"] for s in st)
        entry.update({"stages": st, "start_frame": cur, "end_frame": cur + n, "start_s": round(cur / FPS, 4),
                      "end_s": round((cur + n) / FPS, 4)})
        frames.append(entry)
        cur += n
    return frames


def encode(frames: list[dict], package: Path, work: Path, size, dest: Path) -> dict:
    work.mkdir(parents=True, exist_ok=True)
    lst = work / f"concat_{size[1]}.ffconcat"
    lines = ["ffconcat version 1.0"]
    last = None
    for fr in frames:
        for st in fr["stages"]:
            p = st["image"] if os.path.isabs(st["image"]) else str(package / st["image"])
            lines += [f"file '{p}'", f"duration {st['frames'] / FPS:.10f}"]
            last = p
    lines.append(f"file '{last}'")
    lst.write_text("\n".join(lines) + "\n")
    vf = "fps=30,format=yuv420p" if size == (V.W, V.H) else f"scale={size[0]}:{size[1]}:flags=lanczos,fps=30,format=yuv420p"
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-vf", vf, "-c:v", "libx264",
           "-preset", "medium", "-crf", "18", "-threads", "16", "-movflags", "+faststart", "-an",
           # the concat demuxer's trailing repeated entry adds one frame: pin the exact manifest length
           "-frames:v", str(sum(st["frames"] for fr in frames for st in fr["stages"])), str(dest)]
    t0 = time.perf_counter()
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {r.stderr[-2000:]}")
    return {"file": str(dest), "seconds_to_encode": round(time.perf_counter() - t0, 1), "command": " ".join(cmd),
            "sha256": D.sha(dest)}


def probe_video(path: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries",
                        "stream=width,height,r_frame_rate,nb_read_frames,codec_name,pix_fmt:format=duration",
                        "-of", "json", str(path)], capture_output=True, text=True, check=True)
    j = json.loads(r.stdout)
    s = j["streams"][0]
    num, den = map(int, s["r_frame_rate"].split("/"))
    return {"width": s["width"], "height": s["height"], "fps": num / den, "frames": int(s["nb_read_frames"]),
            "codec": s["codec_name"], "pix_fmt": s["pix_fmt"], "duration_s": float(j["format"]["duration"])}


def video(cache: Path, package: Path, log=print) -> dict:
    cache, package = Path(cache).resolve(), Path(package).resolve()
    fw = D.ic.TruthFirewall(D.PREVIEWS, D.c01.is_evaluation_truth)  # composition: never evaluation truth
    with fw:
        render_m = json.loads((cache / "render-manifest.json").read_text())
        rp = cache / "reference/reference-manifest.json"
        ref_m = json.loads(rp.read_text()) if rp.exists() else None
        frames = sequence(render_m, ref_m)
        total = frames[-1]["end_frame"]
        vids = {}
        for size, name in (((V.W, V.H), "controller-02-classroom-full-1440p.mp4"),
                           ((1920, 1080), "controller-02-classroom-full-1080p.mp4")):
            dest = package / "demo" / name
            info = encode(frames, package, cache / "video-work", size, dest)
            info.update(probe_video(dest))
            vids[name] = info
            log(f"[vl1-video] {name}: {info['width']}x{info['height']} {info['fps']} fps {info['frames']} frames "
                f"{info['duration_s']:.2f} s (expected {total}) sha256 {info['sha256'][:16]}")
    lfm = {"schema": "VisualLanguage1-logical-frames-v1", "fps": FPS, "total_frames": total,
           "total_seconds": round(total / FPS, 4), "logical_frames": frames,
           "videos": {k: {kk: v[kk] for kk in ("width", "height", "fps", "frames", "duration_s", "sha256")} for k, v in vids.items()}}
    D.write_json(package / "demo/logical-frame-manifest.json", lfm)
    times = {}
    for fr in frames:
        key = fr["id"]
        times[key] = f"{fr['start_s']:.1f}–{fr['end_s']:.1f} s"
    loop = f"{frames[[f['id'] for f in frames].index('step_000')]['start_s']:.1f}–" \
           f"{frames[[f['id'] for f in frames].index('step_140')]['end_s']:.1f} s"
    b = render_m["specials"]["bootstrap"]
    (package / "narration.md").write_text(NARRATION.format(
        intro=times["intro"], legend=f"{times['legend']}, {times['guide']}", bootstrap=times["bootstrap"], loop=loop,
        r109=times["event_reactivation_0109"], defer=times["event_defer_0210"], r178=times["event_reactivation_0178"],
        gate=f"{times['residue']}, {times['event_final_residue_gate_0210']}", closure=times["closure"],
        outro=times["outro"] + (f", {times['outro_reference']}" if "outro_reference" in times else ""),
        catalog=b["catalog"], localized=b["localized"], unlocated=b["unlocated"]))
    files = sorted(p.relative_to(package).as_posix() for p in package.rglob("*") if p.is_file()
                   and p.name != "visual-language-manifest.json")
    vlm = {"schema": "VisualLanguage1-package-v1", "contract": "docs/methodology/visual-language-1-contract.md",
           "status": "REVIEW PENDING", "marker": "VISUAL_LANGUAGE_1_CANONICAL_DEMO_COMPLETE (recorded in the report after checks)",
           "sources": {"controller-01-full": D.C01_ACCEPTED, "controller-02-classroom-replay": D.C02_ACCEPTED},
           "paths": {"extract": {"manifest": "extract-manifest.json", "sha256": D.sha(cache / "extract-manifest.json")},
                     "render": {"manifest": "render-manifest.json", "sha256": D.sha(cache / "render-manifest.json")},
                     "reference": None if ref_m is None else {"manifest": "reference/reference-manifest.json",
                                                              "sha256": D.sha(rp)},
                     "video": {"opened_files": sorted(fw.opened), "violations": fw.violations}},
           "videos": vids, "logical_frames": len(frames), "total_seconds": round(total / FPS, 4),
           "pointclouds": render_m["pointclouds"], "reference_products": None if ref_m is None else ref_m["products"],
           "files": {f: {"sha256": D.sha(package / f), "bytes": (package / f).stat().st_size} for f in files}}
    D.write_json(package / "visual-language-manifest.json", vlm)
    return vlm


# ---------------------------------------------------------------- command line

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("extract", help="controller-time extraction into the cache")
    e.add_argument("--source", type=Path, required=True)
    e.add_argument("--replay", type=Path, required=True)
    e.add_argument("--cache", type=Path, required=True)
    r = sub.add_parser("render", help="controller-time frames, events, overview, legend, panoramas, point clouds")
    for k in ("source", "replay", "cache", "out"):
        r.add_argument(f"--{k}", type=Path, required=True)
    r.add_argument("--workers", type=int, default=16)
    f = sub.add_parser("reference", help="the separate REFERENCE / EVALUATION path (after the Blender reference view)")
    for k in ("source", "cache", "out"):
        f.add_argument(f"--{k}", type=Path, required=True)
    v = sub.add_parser("video", help="assemble both MP4s, the logical-frame manifest, narration and the package manifest")
    for k in ("cache", "out"):
        v.add_argument(f"--{k}", type=Path, required=True)
    a = ap.parse_args(argv)
    try:
        if a.cmd == "extract":
            D.extract(a.source, a.replay, a.cache)
        elif a.cmd == "render":
            m = render(a.source, a.replay, a.cache, a.out, a.workers)
            if m["firewall_violations"]:
                print(f"[vl1-render] REFUSED: firewall violations {m['firewall_violations']}")
                return 1
        elif a.cmd == "reference":
            m = reference(a.source, a.cache, a.out)
            print(f"[vl1-reference] products {sorted(m['products'])}; omitted: {m['omitted_reason']}")
        else:
            m = video(a.cache, a.out)
            print(f"[vl1-video] {m['logical_frames']} logical frames, {m['total_seconds']} s; "
                  f"{len(m['files'])} package files")
    except D.ExtractionMismatch as exc:
        print(f"[vl1-{a.cmd}] STOP: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
