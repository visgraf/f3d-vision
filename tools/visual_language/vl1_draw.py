"""Visual Language 1: drawing — the head chart, the standard 3-D camera, panels, roster, timeline.

Contract: docs/methodology/visual-language-1-contract.md.  Colors, cues and glyphs come from
style.py only.
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import style as S

W, H = 2560, 1440
HEADER_H = 84
PANEL_W, PANEL_H, GAP = 1256, 546, 16
PANEL_XY = [(16, 92), (16 + PANEL_W + GAP, 92), (16, 92 + PANEL_H + 12), (16 + PANEL_W + GAP, 92 + PANEL_H + 12)]
TITLE_H = 46
CONTENT_W, CONTENT_H = PANEL_W, PANEL_H - TITLE_H
ROSTER_Y, ROSTER_H = 1208, 76
TIMELINE_Y = 1292
CODE = {"TARGET_SUPPORT": 1, "OTHER_SURFACE": 2, "UNKNOWN": 3, "AMBIGUOUS_BOUNDARY": 4, "TARGET_EVIDENCE_UNMAPPED": 5}


# ---------------------------------------------------------------- the head-centred chart

class Chart:
    """A yaw/pitch window of the fixed-head chart at ``ppd`` pixels per degree."""

    def __init__(self, yaw0, yaw1, pit0, pit1, ppd):
        self.y0, self.y1, self.p0, self.p1, self.s = float(yaw0), float(yaw1), float(pit0), float(pit1), float(ppd)
        self.w, self.h = int(round((yaw1 - yaw0) * ppd)), int(round((pit1 - pit0) * ppd))

    def px(self, yaw, pitch):
        return (np.asarray(yaw, float) - self.y0) * self.s, (self.p1 - np.asarray(pitch, float)) * self.s

    def pt(self, yp):
        x, y = self.px(yp[0], yp[1])
        return float(x), float(y)

    def inside(self, yp, margin=0.0):
        return self.y0 - margin <= yp[0] <= self.y1 + margin and self.p0 - margin <= yp[1] <= self.p1 + margin


def fit_window(points_yp, *, min_w=8.0, aspect=621 / 330, margin=1.5, clip=((-25.0, 25.0), (-20.0, 20.0))):
    """A window (yaw0, yaw1, pit0, pit1) containing the points, with a fixed aspect ratio."""
    pts = np.asarray(points_yp, float).reshape(-1, 2)
    y0, y1 = float(pts[:, 0].min()) - margin, float(pts[:, 0].max()) + margin
    p0, p1 = float(pts[:, 1].min()) - margin, float(pts[:, 1].max()) + margin
    w, h = max(y1 - y0, min_w), max(p1 - p0, min_w / aspect)
    if w / h < aspect:
        w = h * aspect
    else:
        h = w / aspect
    cy, cp = (y0 + y1) / 2, (p0 + p1) / 2
    w, h = min(w, clip[0][1] - clip[0][0]), min(h, clip[1][1] - clip[1][0])
    cy = min(max(cy, clip[0][0] + w / 2), clip[0][1] - w / 2)
    cp = min(max(cp, clip[1][0] + h / 2), clip[1][1] - h / 2)
    return cy - w / 2, cy + w / 2, cp - h / 2, cp + h / 2


def splat(chart: Chart, xyz, colors, img=None, radius=0, bg=S.PANEL):
    """Nearest-surface point splats in a chart window (z-buffer by range)."""
    out = np.full((chart.h, chart.w, 3), bg, np.uint8) if img is None else img
    xyz = np.asarray(xyz, np.float64).reshape(-1, 3)
    if not len(xyz):
        return out
    yaw = np.degrees(np.arctan2(xyz[:, 0], -xyz[:, 2]))
    pit = np.degrees(np.arctan2(xyz[:, 1], np.hypot(xyz[:, 0], xyz[:, 2])))
    x, y = chart.px(yaw, pit)
    cols = np.broadcast_to(np.asarray(colors, np.uint8), (len(xyz), 3))
    rng = np.linalg.norm(xyz, axis=1)
    offs = [(dx, dy) for dx in range(-radius, radius + 1) for dy in range(-radius, radius + 1) if dx * dx + dy * dy <= radius * radius]
    xi = np.concatenate([np.floor(x).astype(np.int64) + dx for dx, _ in offs])
    yi = np.concatenate([np.floor(y).astype(np.int64) + dy for _, dy in offs])
    rr = np.tile(rng, len(offs)) + np.repeat([0.0 if o == (0, 0) else 1e-3 for o in offs], len(rng))
    idx = np.tile(np.arange(len(rng)), len(offs))
    ok = (xi >= 0) & (xi < chart.w) & (yi >= 0) & (yi < chart.h)
    flat, rr, idx = yi[ok] * chart.w + xi[ok], rr[ok], idx[ok]
    if not len(flat):
        return out
    order = np.lexsort((rr, flat))
    first = np.r_[True, flat[order][1:] != flat[order][:-1]]
    sel = order[first]
    out.reshape(-1, 3)[flat[sel]] = cols[idx[sel]]
    return out


def cells(chart: Chart, grid: np.ndarray, domain=((-25.0, 25.0), (-20.0, 20.0)), grid_deg=0.10) -> np.ndarray:
    """Nearest resampling of a 0.1-degree controller chart array into a chart window (-1 outside)."""
    yy, xx = np.mgrid[0:chart.h, 0:chart.w]
    yaw = chart.y0 + (xx + 0.5) / chart.s
    pit = chart.p1 - (yy + 0.5) / chart.s
    cx = np.rint((yaw - domain[0][0]) / grid_deg).astype(int)
    cy = np.rint((pit - domain[1][0]) / grid_deg).astype(int)
    h, w = grid.shape
    inside = (cx >= 0) & (cx < w) & (cy >= 0) & (cy < h)
    out = np.full((chart.h, chart.w), -1, np.int32)
    out[inside] = grid[cy[inside], cx[inside]]
    return out


def epistemic_image(chart: Chart, class_code: np.ndarray, stipple_spacing=9) -> Image.Image:
    """E_t(i): target support, other surface, unknown (stippled) and ambiguous boundary (strokes)."""
    c = cells(chart, class_code)
    img = np.full((chart.h, chart.w, 3), S.UNKNOWN_BG, np.uint8)
    img[c == CODE["OTHER_SURFACE"]] = S.OTHER_SURF
    img[(c == CODE["TARGET_SUPPORT"]) | (c == CODE["TARGET_EVIDENCE_UNMAPPED"])] = S.OI_SKY
    img[c < 0] = (236, 235, 231)
    im = Image.fromarray(img)
    unknown = Image.fromarray(((c == CODE["UNKNOWN"]) * 255).astype(np.uint8))
    dots = Image.new("RGB", im.size, S.UNKNOWN_BG)
    S.stipple(dots, (0, 0, im.size[0], im.size[1]), spacing=stipple_spacing, r=1)
    im.paste(dots, (0, 0), unknown)
    amb = (c == CODE["AMBIGUOUS_BOUNDARY"]).astype(np.uint8)
    if amb.any():
        size = 1 + 2 * (max(1, int(round(chart.s / 12.5))) // 2)
        amb = amb * 255 if size < 3 else np.asarray(Image.fromarray(amb * 255).filter(ImageFilter.MaxFilter(size)))
        arr = np.asarray(im).copy()
        arr[amb > 0] = S.OI_ORANGE
        im = Image.fromarray(arr)
    tgt = ((c == CODE["TARGET_SUPPORT"]) | (c == CODE["TARGET_EVIDENCE_UNMAPPED"])).astype(np.uint8)
    outline(im, tgt, (10, 60, 110), width=2)
    return im


def outline(im: Image.Image, mask: np.ndarray, color, width=3, halo=None):
    import cv2
    m = np.ascontiguousarray(mask.astype(np.uint8))
    if not m.any():
        return
    contours, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    arr = np.asarray(im).copy()
    if halo is not None:
        cv2.drawContours(arr, contours, -1, halo, width + 4)
    cv2.drawContours(arr, contours, -1, color, width)
    im.paste(Image.fromarray(arr))


def grid_lines(im: Image.Image, chart: Chart, step=5.0, color=(0, 0, 0), alpha=40, labels=True):
    ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    y = math.ceil(chart.y0 / step) * step
    while y <= chart.y1 + 1e-9:
        x, _ = chart.px(y, 0)
        d.line([float(x), 0, float(x), chart.h], fill=color + (alpha if abs(y) > 1e-9 else alpha * 2,), width=1)
        y += step
    p = math.ceil(chart.p0 / step) * step
    while p <= chart.p1 + 1e-9:
        _, yy = chart.px(0, p)
        d.line([0, float(yy), chart.w, float(yy)], fill=color + (alpha if abs(p) > 1e-9 else alpha * 2,), width=1)
        p += step
    im.paste(ov, (0, 0), ov)
    if labels:
        d2 = ImageDraw.Draw(im)
        S.text(d2, (6, chart.h - 28), f"yaw {chart.y0:+.0f}..{chart.y1:+.0f}°, pitch {chart.p0:+.0f}..{chart.p1:+.0f}°",
               size=S.T_SMALL - 3, fill=S.INK2)


# ---------------------------------------------------------------- the standard head-relative 3-D camera

class Camera3D:
    """Orthographic view from above and behind the fixed head (head frame: x right, y up, -z forward)."""

    ELEV, AZIM = 38.0, -18.0

    def __init__(self, bounds_uv=None):
        a, e = math.radians(self.AZIM), math.radians(self.ELEV)
        ry = np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]])
        rx = np.array([[1, 0, 0], [0, math.cos(e), -math.sin(e)], [0, math.sin(e), math.cos(e)]])
        self.R = rx @ ry
        self.bounds = bounds_uv

    def project(self, xyz):
        q = np.asarray(xyz, np.float64).reshape(-1, 3) @ self.R.T
        return q[:, 0], -q[:, 1], -q[:, 2]

    def fit(self, xyz, lo=0.3, hi=99.7):
        u, v, _ = self.project(xyz)
        uv = np.c_[u, v]
        a, b = np.percentile(uv, lo, axis=0), np.percentile(uv, hi, axis=0)
        # the fixed head (origin) stays in frame: the view is head-relative
        a, b = np.minimum(a, [-0.25, -0.25]), np.maximum(b, [0.25, 0.25])
        self.bounds = (a.tolist(), b.tolist())
        return self.bounds


class View3D:
    """A pixel window of the camera: the full scene, or a zoomed inset around some points."""

    def __init__(self, cam: Camera3D, size, bounds=None, pad=24):
        self.cam, self.size, self.pad = cam, (int(size[0]), int(size[1])), pad
        (u0, v0), (u1, v1) = bounds if bounds is not None else cam.bounds
        sc = min((self.size[0] - 2 * pad) / max(u1 - u0, 1e-9), (self.size[1] - 2 * pad) / max(v1 - v0, 1e-9))
        self.sc = sc
        self.u0 = (u0 + u1) / 2 - (self.size[0] / 2) / sc
        self.v0 = (v0 + v1) / 2 - (self.size[1] / 2) / sc

    def xy(self, xyz):
        u, v, d = self.cam.project(xyz)
        return (u - self.u0) * self.sc, (v - self.v0) * self.sc, d

    def zoom_bounds(self, xyz, lo=1.0, hi=99.0, margin=0.35, min_extent=0.8):
        u, v, _ = self.cam.project(xyz)
        a = np.percentile(np.c_[u, v], lo, axis=0) - margin
        b = np.percentile(np.c_[u, v], hi, axis=0) + margin
        c, e = (a + b) / 2, np.maximum(b - a, min_extent)
        return ((c - e / 2).tolist(), (c + e / 2).tolist())

    def render(self, xyz, colors, img=None, bg=S.PANEL, radius=0):
        out = np.full((self.size[1], self.size[0], 3), bg, np.uint8) if img is None else img
        x, y, d = self.xy(xyz)
        if not len(x):
            return out
        cols = np.broadcast_to(np.asarray(colors, np.uint8), (len(x), 3))
        offs = [(dx, dy) for dx in range(-radius, radius + 1) for dy in range(-radius, radius + 1)]
        xi = np.concatenate([np.floor(x).astype(np.int64) + dx for dx, _ in offs])
        yi = np.concatenate([np.floor(y).astype(np.int64) + dy for _, dy in offs])
        dd = np.tile(d, len(offs))
        idx = np.tile(np.arange(len(x)), len(offs))
        ok = (xi >= 0) & (xi < self.size[0]) & (yi >= 0) & (yi < self.size[1])
        flat = yi[ok] * self.size[0] + xi[ok]
        if not len(flat):
            return out
        order = np.lexsort((dd[ok], flat))
        first = np.r_[True, flat[order][1:] != flat[order][:-1]]
        sel = order[first]
        out.reshape(-1, 3)[flat[sel]] = cols[idx[ok][sel]]
        return out

    def occupied_cells(self, xyz, cell):
        """Screen cells (centers) that contain projected points: a lattice for ring / x marks."""
        x, y, _ = self.xy(xyz)
        ok = (x >= 0) & (x < self.size[0]) & (y >= 0) & (y < self.size[1])
        if not ok.any():
            return np.empty((0, 2))
        c = np.unique(np.c_[np.floor(x[ok] / cell), np.floor(y[ok] / cell)].astype(np.int64), axis=0)
        return (c + 0.5) * cell


def depth_shade(xyz, cam: Camera3D, near=S.GEOM_NEAR, far=S.GEOM_FAR, dlim=None):
    _, _, d = cam.project(xyz)
    lo, hi = dlim if dlim is not None else (np.percentile(d, 1), np.percentile(d, 99))
    t = np.clip((d - lo) / max(hi - lo, 1e-9), 0, 1)[:, None]
    return (np.asarray(near) * (1 - t) + np.asarray(far) * t).astype(np.uint8)


def lattice_marks(img: Image.Image, cells_xy, kind, color, r=4, width=2):
    d = ImageDraw.Draw(img)
    for x, y in cells_xy:
        if kind == "ring":
            S.ring(d, x, y, r=r, color=color, width=width)
        elif kind == "x":
            S.xmark(d, x, y, r=r, color=color, width=width)
        elif kind == "square":
            S.square(d, x, y, r=r, color=color)


def head_glyph(img: Image.Image, view: View3D, gaze_end=None):
    d = ImageDraw.Draw(img)
    hx, hy, _ = view.xy(np.zeros((1, 3)))
    hx, hy = float(hx[0]), float(hy[0])
    if gaze_end is not None:
        gx, gy, _ = view.xy(np.asarray(gaze_end, float).reshape(1, 3))
        S.dashed_line(d, [(hx, hy), (float(gx[0]), float(gy[0]))], S.INK, width=2, dash=8, gap=6)
    d.ellipse([hx - 11, hy - 11, hx + 11, hy + 11], fill=S.WHITE, outline=S.INK, width=3)
    for ex in (-0.0315, 0.0315):
        x, y, _ = view.xy(np.array([[ex * 6, 0.0, -0.05]]))
        d.ellipse([float(x[0]) - 3, float(y[0]) - 3, float(x[0]) + 3, float(y[0]) + 3], fill=S.INK)
    S.text(d, (hx + 14, hy - 12), "head", size=S.T_SMALL - 2, fill=S.INK2)


# ---------------------------------------------------------------- panels and frame furniture

def panel(canvas: Image.Image, index: int, number: str, title: str, tag: str, badges: list[str], content: Image.Image):
    """A cockpit panel: number, title, temporal tag (BEFORE / OBSERVATION / AFTER), truth badges."""
    x, y = PANEL_XY[index]
    d = ImageDraw.Draw(canvas)
    d.rectangle([x, y, x + PANEL_W - 1, y + PANEL_H - 1], fill=S.PANEL, outline=(205, 204, 199), width=2)
    d.rectangle([x, y, x + PANEL_W - 1, y + TITLE_H], fill=(238, 237, 233))
    d.text((x + 12, y + 8), number, font=S.font(S.T_HEAD, True), fill=S.INK)
    nx = x + 12 + d.textlength(number, font=S.font(S.T_HEAD, True)) + 12
    d.text((nx, y + 8), title, font=S.font(S.T_HEAD, True), fill=S.INK)
    tx = nx + d.textlength(title, font=S.font(S.T_HEAD, True)) + 16
    if tag:
        f = S.font(S.T_SMALL, True)
        tw = d.textlength(tag, font=f)
        d.rectangle([tx, y + 9, tx + tw + 16, y + 38], fill=S.INK)
        d.text((tx + 8, y + 12), tag, font=f, fill=S.WHITE)
    bx = x + PANEL_W - 10
    for b in reversed(badges):
        bx = S.badge(canvas, bx, y + 7, b) - 8
    canvas.paste(content.crop((0, 0, CONTENT_W, CONTENT_H)), (x, y + TITLE_H))
    d.rectangle([x, y, x + PANEL_W - 1, y + PANEL_H - 1], outline=(205, 204, 199), width=2)


def header(canvas: Image.Image, headline: str, sub: str, phase: str, step_text: str):
    d = ImageDraw.Draw(canvas)
    d.rectangle([0, 0, W, HEADER_H], fill=S.WHITE)
    d.line([0, HEADER_H, W, HEADER_H], fill=(205, 204, 199), width=2)
    d.text((18, 10), "FOVEAL STEREO VISION", font=S.font(S.T_SMALL, True), fill=S.INK2)
    d.text((18, 36), "Controller-02 · Classroom", font=S.font(S.T_HEAD, True), fill=S.INK)
    tag = "CONTROLLED PROOF OF CONCEPT"
    f = S.font(S.T_SMALL - 2, True)
    tx = 18 + d.textlength("FOVEAL STEREO VISION", font=S.font(S.T_SMALL, True)) + 16
    tw = d.textlength(tag, font=f)
    d.rectangle([tx, 8, tx + tw + 14, 32], outline=S.INK, width=2)
    d.text((tx + 7, 10), tag, font=f, fill=S.INK)
    x = 640
    d.text((x, 8), headline, font=S.font(S.T_TITLE + 4, True), fill=S.INK)
    d.text((x, 50), sub, font=S.font(S.T_SMALL), fill=S.INK2)
    # phase badge and step counter on the right
    f2 = S.font(S.T_HEAD, True)
    sw = d.textlength(step_text, font=S.font(S.T_BIG, True))
    d.text((W - 24 - sw, 18), step_text, font=S.font(S.T_BIG, True), fill=S.INK)
    pw = d.textlength(phase, font=f2) + 28
    px0 = W - 24 - sw - 24 - pw
    box = [px0, 20, px0 + pw, 62]
    if phase == "NORMAL":
        d.rectangle(box, fill=S.WHITE, outline=S.INK, width=3)
        d.text((px0 + 14, 26), phase, font=f2, fill=S.INK)
    elif phase == "RESIDUE":
        d.rectangle(box, fill=(253, 243, 222))
        S.hatch(canvas, box, S.OI_ORANGE, spacing=10, width=3)
        d = ImageDraw.Draw(canvas)
        d.rectangle(box, outline=S.OI_ORANGE, width=3)
        tb = d.textbbox((px0 + 14, 26), phase, font=f2)
        d.rectangle([tb[0] - 4, tb[1] - 2, tb[2] + 4, tb[3] + 2], fill=S.WHITE)
        d.text((px0 + 14, 26), phase, font=f2, fill=S.INK)
    else:
        d.rectangle(box, fill=S.INK)
        d.text((px0 + 14, 26), phase, font=f2, fill=S.WHITE)


def roster(canvas: Image.Image, states: dict[int, str], current: int | None, y=ROSTER_Y, unlocated=209):
    """The 25 localized objects' service states (tiles) plus the unlocated count."""
    d = ImageDraw.Draw(canvas)
    d.text((18, y + 4), "OBJECTS", font=S.font(S.T_SMALL, True), fill=S.INK2)
    d.text((18, y + 30), "service", font=S.font(S.T_SMALL - 2), fill=S.INK2)
    d.text((18, y + 52), "state", font=S.font(S.T_SMALL - 2), fill=S.INK2)
    ids = sorted(states)
    x0, tw, gap = 132, 86, 6
    for n, i in enumerate(ids):
        bx = x0 + n * (tw + gap)
        box = [bx, y + 4, bx + tw, y + ROSTER_H - 4]
        S.state_tile(canvas, box, states[i], str(i), size=S.T_BODY)
        if i == current:
            d = ImageDraw.Draw(canvas)
            d.rectangle([box[0] - 5, box[1] - 5, box[2] + 5, box[3] + 5], outline=S.INK, width=4)
    bx = x0 + len(ids) * (tw + gap) + 10
    box = [bx, y + 4, bx + 150, y + ROSTER_H - 4]
    S.state_tile(canvas, box, "UNLOCATED", f"{unlocated}", size=S.T_BODY)


def tile_state(label: str) -> str:
    """Controller-02 service-state label -> tile state."""
    if label.startswith("FINALIZED") or label.endswith("final_probe_rejected"):
        return "RESIDUAL"
    if "DEFERRED" in label:
        return "DEFERRED"
    return label.split("/")[0].split(":")[0]


def timeline(canvas: Image.Image, actions: list[dict], events: list[dict], current: int | None, *, phase_cells=None,
             y=TIMELINE_Y, highlight=None):
    """141 columns: action source, object bouts, events; the playhead; NORMAL -> RESIDUE -> CLOSED."""
    d = ImageDraw.Draw(canvas)
    x0, x1 = 132, W - 300
    n = len(actions)
    cw = (x1 - x0) / n
    d.text((18, y + 2), "TIMELINE", font=S.font(S.T_SMALL, True), fill=S.INK2)
    d.text((18, y + 28), "source", font=S.font(S.T_SMALL - 3), fill=S.INK2)
    d.text((18, y + 58), "object", font=S.font(S.T_SMALL - 3), fill=S.INK2)
    d.text((18, y + 90), "events", font=S.font(S.T_SMALL - 3), fill=S.INK2)
    done = (lambda s: True) if current is None else (lambda s: s <= current)
    # object bouts row
    prev = None
    bout = 0
    for a in actions:
        s = a["global_step"]
        if a["target_id"] != prev:
            bout += 1
            prev = a["target_id"]
            if s > 0:
                xx = x0 + s * cw
                d.line([xx, y + 50, xx, y + 84], fill=S.INK, width=2)
        fill = (214, 213, 208) if bout % 2 else (232, 231, 226)
        if not done(s):
            fill = (245, 245, 243)
        d.rectangle([x0 + s * cw, y + 54, x0 + (s + 1) * cw - 1, y + 80], fill=fill)
    # object labels at bout starts (when room)
    prev, last_x = None, -99
    for a in actions:
        s = a["global_step"]
        if a["target_id"] != prev:
            prev = a["target_id"]
            xx = x0 + s * cw + 2
            if xx - last_x > 34:
                d.text((xx, y + 57), str(a["target_id"]), font=S.font(S.T_SMALL - 5, True),
                       fill=S.INK if done(s) else S.MUTED)
                last_x = xx
    # source row
    for a in actions:
        s = a["global_step"]
        cx, cy = x0 + (s + 0.5) * cw, y + 36
        _lab, col, shape = S.SOURCES[a["action_source"]]
        if not done(s):
            col = tuple(int(c * 0.3 + 255 * 0.7) for c in col)
        r = min(7, cw * 0.45)
        if shape == "square":
            d.rectangle([cx - r, cy - r, cx + r, cy + r], fill=col)
        elif shape == "circle":
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
        else:
            d.polygon([(cx, cy - r - 1), (cx + r + 1, cy), (cx, cy + r + 1), (cx - r - 1, cy)], fill=col)
    # events row
    for e in events:
        s = e["global_step"]
        if s >= n:
            continue
        cx, cy = x0 + (s + 0.5) * cw, y + 100
        vis = done(s)
        if e["event"] == "quiet":
            d.text((cx - 6, cy - 12), "✓", font=S.font(S.T_SMALL - 2, True), fill=S.INK if vis else S.FAINT)
        elif e["event"] == "natural_reactivation":
            col = S.OI_YELLOW if vis else (250, 246, 210)
            d.polygon([(cx, cy - 12), (cx - 9, cy + 6), (cx + 9, cy + 6)], fill=col, outline=S.INK if vis else S.FAINT)
            if vis:
                S.text(d, (cx + 8, cy + 4), f"{e['object']}", size=S.T_SMALL - 5, bold=True)
        elif e["event"] == "deferred":
            if vis:
                band = [cx + cw / 2, y + 88, x0 + n * cw, y + 118]
                if current is not None:
                    band[2] = min(band[2], x0 + (current + 1) * cw)
                if band[2] > band[0]:
                    S.hatch(canvas, band, S.OI_ORANGE, spacing=9, width=2)
                    d = ImageDraw.Draw(canvas)
                    d.rectangle(band, outline=S.OI_ORANGE, width=2)
                d.polygon([(cx, cy - 13), (cx + 11, cy), (cx, cy + 13), (cx - 11, cy)], fill=S.OI_ORANGE, outline=S.INK)
                S.text(d, (cx + 16, cy - 10), "210 DEFERRED", size=S.T_SMALL - 4, bold=True, plate=S.WHITE)
            else:
                d.polygon([(cx, cy - 13), (cx + 11, cy), (cx, cy + 13), (cx - 11, cy)], outline=S.FAINT)
    # phase cells after the last action: RESIDUE, CLOSED
    px = x0 + n * cw + 10
    labels = phase_cells or {}
    for name in ("RESIDUE", "CLOSED"):
        state = labels.get(name, "future")
        box = [px, y + 50, px + 72, y + 84]
        if state == "future":
            S.dashed_rect(d, box, S.FAINT, width=2, dash=5, gap=4)
            d.text((px + 6, y + 58), name, font=S.font(S.T_SMALL - 6, True), fill=S.FAINT)
        elif name == "RESIDUE":
            d.rectangle(box, fill=(253, 243, 222))
            S.hatch(canvas, box, S.OI_ORANGE, spacing=9, width=2)
            d = ImageDraw.Draw(canvas)
            d.rectangle(box, outline=S.OI_ORANGE, width=3)
            S.text(d, (px + 6, y + 58), name, size=S.T_SMALL - 6, bold=True, plate=S.WHITE)
        else:
            d.rectangle(box, fill=S.INK)
            d.text((px + 8, y + 58), name, font=S.font(S.T_SMALL - 6, True), fill=S.WHITE)
        if state == "current":
            d.rectangle([box[0] - 4, box[1] - 4, box[2] + 4, box[3] + 4], outline=S.INK, width=3)
        px += 82
    # step axis ticks
    for s in range(0, n, 10):
        xx = x0 + s * cw
        d.line([xx, y + 122, xx, y + 130], fill=S.INK2, width=1)
        d.text((xx - 6, y + 128), str(s), font=S.font(S.T_SMALL - 7), fill=S.INK2)
    # playhead
    if current is not None and 0 <= current < n:
        cx = x0 + (current + 0.5) * cw
        d.line([cx, y + 20, cx, y + 120], fill=S.INK, width=3)
        d.polygon([(cx - 9, y + 8), (cx + 9, y + 8), (cx, y + 20)], fill=S.INK)
    if highlight is not None:
        s0, s1 = highlight
        d.rectangle([x0 + s0 * cw - 2, y + 22, x0 + (s1 + 1) * cw + 2, y + 120], outline=S.INK, width=3)
    # timeline legend (right)
    lx = W - 132
    for k, (src, (lab, col, shape)) in enumerate(S.SOURCES.items()):
        yy = y + 20 + k * 26
        if shape == "square":
            d.rectangle([lx - 20, yy + 3, lx - 8, yy + 15], fill=col)
        elif shape == "circle":
            d.ellipse([lx - 20, yy + 3, lx - 8, yy + 15], fill=col)
        else:
            d.polygon([(lx - 14, yy + 1), (lx - 6, yy + 9), (lx - 14, yy + 17), (lx - 22, yy + 9)], fill=col)
        d.text((lx, yy), lab.split()[0], font=S.font(S.T_SMALL - 4), fill=S.INK2)
    d.text((lx - 20, y + 98), "✓ quiet  ▲ react.", font=S.font(S.T_SMALL - 6), fill=S.INK2)


def plate_lines(img: Image.Image, xy, lines, size=S.T_BODY, gap=8, bold_first=False, fill=S.INK):
    d = ImageDraw.Draw(img)
    x, y = xy
    for n, ln in enumerate(lines):
        if isinstance(ln, tuple):
            s, kw = ln
        else:
            s, kw = ln, {}
        b = kw.get("bold", bold_first and n == 0)
        sz = kw.get("size", size)
        d.text((x, y), s, font=S.font(sz, b), fill=kw.get("fill", fill))
        y += sz + gap
    return y
