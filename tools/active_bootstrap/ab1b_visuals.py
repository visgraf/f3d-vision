"""Active Bootstrap-1b: the persistent human-facing figures of gaze-centered spherical epipolar geometry.

Contract: docs/active-bootstrap/ab1b-spherical-epipolar-geometry-contract.md, section 18.  Reads the saved AB1a pair and
calibration (the same observation), the AB1b oracle / geometry / evaluation products and, for the comparison, the
accepted AB1a pre-look record.  Draws with the accepted Visual Language 1 style (read-only).

Truth classes: ORACLE INPUT (the rendered RGB pair; Position / Object Index as used by the oracle), DERIVED (raw-core
rays, theta / phi, the display chart, truth-stripped correspondences, disparity, P_epi, P_ray, conditioning),
REFERENCE / EVALUATION (Position when scoring; the AB1a planar result).  Nothing is CONTROLLER-TIME.  Glyphs: solid
crosshair = the executed gaze #1; x = the +X baseline pole; dashed square = the nominal 12-degree raw core; small solid
box = the raw source of the AB1a rectified core.  The display chart (chart_u, chart_v) is a diagnostic chart only, not a
matcher raster.  Deterministic: the checker regenerates every PNG byte-identically.
"""
from __future__ import annotations

import hashlib
import io
import json
import math
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
for _p in (HERE, TOOLS, TOOLS / "classroom_oracle", TOOLS / "visual_language"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import ab1b_spec as SP  # noqa: E402
import breadth1_visuals as B  # noqa: E402  (accepted Breadth-1 helpers, read-only)
import fsg_geometry as FG  # noqa: E402  (accepted, read-only)
import style as S  # noqa: E402  (Visual Language 1, read-only)

ORA, DER, REF = SP.TRUTH_ORACLE, SP.TRUTH_DERIVED, SP.TRUTH_REFERENCE
SMALL = 17
FIGURES = ["overview.png", "raw-foveal-core.png", "spherical-epipolar-core.png", "perfect-correspondences.png",
           "epipolar-residual.png", "angular-disparity.png", "conditioning.png", "reconstructed-point-cloud.png",
           "triangulation-error.png", "planar-vs-spherical.png"]
BADGES = {"overview.png": [ORA, DER, REF], "raw-foveal-core.png": [ORA, DER], "spherical-epipolar-core.png": [DER, ORA],
          "perfect-correspondences.png": [ORA, DER], "epipolar-residual.png": [DER], "angular-disparity.png": [DER],
          "conditioning.png": [DER], "reconstructed-point-cloud.png": [DER], "triangulation-error.png": [REF, DER],
          "planar-vs-spherical.png": [REF, DER]}
NOT_STATEMENT = ("Not a matcher, not SGBM, not a global spherical warp: one fixation, its raw 12° support, physical rays "
                 "in baseline-polar coordinates, perfect correspondence supplied by an oracle.")
# single-hue sequential ramps (light -> dark) and one diverging pair with a neutral midpoint (Visual Language 1 hues)
RANGE_RAMP = (np.array([214, 229, 247.]), np.array([8, 48, 107.]))
DISP_RAMP = (np.array([253, 236, 210.]), np.array([140, 45, 4.]))
ERR_RAMP = (np.array([239, 230, 240.]), np.array([96, 22, 92.]))
COND_RAMP = (np.array([229, 245, 224.]), np.array([0, 90, 50.]))
DIV_NEG, DIV_MID, DIV_POS = np.array(S.OI_BLUE, float), np.array([236, 235, 232.]), np.array(S.OI_VERM, float)
EMPTY = (247, 246, 242)
NOCORR = (232, 230, 225)


def sha256(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=False, compress_level=6)
    return buf.getvalue()


def gamma(rgb_linear) -> np.ndarray:
    return B.gamma_u8(rgb_linear)


class Data:
    def __init__(self, run: Path):
        self.run = run
        src = SP.AB1A_RUN
        j = lambda p: json.loads(Path(p).read_text())  # noqa: E731
        self.c = j(src / SP.CALIBRATION_REL)
        self.pre = j(src / "prelook/prelook-geometry.json")
        self.osum = j(run / "oracle/oracle-summary.json")
        self.gsum = j(run / "geometry/geometry-summary.json")
        self.ev = j(run / "evaluation/evaluation-summary.json")
        with np.load(src / SP.RGB_REL) as z:
            self.rgb = {k: np.asarray(z[k]) for k in ("rgb_L", "rgb_R")}
        npz = lambda p: {k: np.asarray(v) for k, v in np.load(run / p).items()}  # noqa: E731
        self.rays = npz("geometry/left-core-rays.npz")
        self.res = npz("geometry/epipolar-result.npz")
        self.prod = npz("oracle/oracle-correspondences.npz")
        self.evr = npz("evaluation/evaluation-result.npz")
        self.sources = {str(p): sha256(p) for p in (src / SP.CALIBRATION_REL, src / SP.RGB_REL,
                                                    src / "prelook/prelook-geometry.json")}
        self.sources.update({n: sha256(run / n) for n in (
            "oracle/oracle-summary.json", "oracle/oracle-correspondences.npz", "geometry/geometry-summary.json",
            "geometry/left-core-rays.npz", "geometry/epipolar-result.npz", "evaluation/evaluation-summary.json",
            "evaluation/evaluation-result.npz")})
        self.yaw, self.pitch = self.c["gaze_yaw_pitch_deg"]
        n = SP.CORE_SIZE
        self.n = len(self.prod["left_core_row"])
        self.mask = np.zeros((n, n), bool)
        self.mask[self.res["left_core_row"], self.res["left_core_col"]] = True
        self.ve = self.res["valid_epi"].astype(bool)
        self.core_rgb = self.rgb["rgb_L"][SP.CORE_ORIGIN:SP.CORE_ORIGIN + n, SP.CORE_ORIGIN:SP.CORE_ORIGIN + n]
        self.tg, self.pg = self.gsum["theta_g_rad"], self.gsum["phi_g_rad"]

    def grid(self, values, fill=np.nan) -> np.ndarray:
        n = SP.CORE_SIZE
        out = np.full((n, n), fill, np.float64)
        out[self.res["left_core_row"], self.res["left_core_col"]] = values
        return out


# ------------------------------------------------------------------ drawing helpers
def ramp(t, ends) -> np.ndarray:
    t = np.clip(np.asarray(t, np.float64), 0, 1)[..., None]
    return np.rint(ends[0] * (1 - t) + ends[1] * t).astype(np.uint8)


def diverging(t) -> np.ndarray:
    t = np.clip(np.asarray(t, np.float64), -1, 1)[..., None]
    neg = DIV_MID * (1 + t) + DIV_NEG * (-t)
    pos = DIV_MID * (1 - t) + DIV_POS * t
    return np.rint(np.where(t < 0, neg, pos)).astype(np.uint8)


def nearest(a: np.ndarray, size: int) -> Image.Image:
    return Image.fromarray(a).resize((size, size), Image.NEAREST)


def frame(dr, x, y, w, h, color=S.INK2, width=1) -> None:
    dr.rectangle([x - 1, y - 1, x + w, y + h], outline=color, width=width)


def caption(dr, x, y, s, size=SMALL, bold=False, fill=S.INK, anchor="la"):
    return S.text(dr, (x, y), s, size=size, bold=bold, fill=fill, outline=None, anchor=anchor)


def header(img, title, lines, badges) -> None:
    B.header(img, title, lines, badges)


def region(img, x, y, w, h, letter, title, badges) -> None:
    dr = ImageDraw.Draw(img)
    dr.rounded_rectangle([x, y, x + w, y + h], radius=10, outline=S.FAINT, width=2, fill=S.PANEL)
    S.text(dr, (x + 18, y + 14), f"{letter} — {title}", size=S.T_HEAD, bold=True, outline=None)
    xr = x + w - 16
    for b in badges:
        xr = S.badge(img, xr, y + 12, b) - 10


def statement(img, x, y, w, h, lines) -> None:
    dr = ImageDraw.Draw(img)
    dr.rectangle([x, y, x + w - 1, y + h - 1], fill=EMPTY)
    S.hatch(img, [x, y, x + w, y + h], (226, 224, 218), spacing=12, width=1)
    dr = ImageDraw.Draw(img)
    frame(dr, x, y, w, h)
    y0 = y + h / 2 - 15 * len(lines)
    for k, ln in enumerate(lines):
        S.text(dr, (x + w / 2, y0 + 30 * k), ln, size=SMALL + (2 if k == 0 else 0), bold=k == 0, plate=EMPTY, anchor="mm")


def colorbar(img, x, y, w, h, lo, hi, ends=None, div=False, label="", fmt="{:.2f}") -> None:
    dr = ImageDraw.Draw(img)
    t = np.linspace(0, 1, w)[None, :].repeat(h, 0)
    bar = diverging(2 * t - 1) if div else ramp(t, ends)
    img.paste(Image.fromarray(bar), (int(x), int(y)))
    frame(dr, x, y, w, h)
    caption(dr, x, y + h + 4, fmt.format(lo), size=14, fill=S.INK2)
    caption(dr, x + w, y + h + 4, fmt.format(hi), size=14, fill=S.INK2, anchor="ra")
    if div:
        caption(dr, x + w / 2, y + h + 4, "0", size=14, fill=S.INK2, anchor="ma")
    caption(dr, x + w / 2, y - 4, label, size=14, fill=S.INK2, anchor="md")


def layer(d: Data, values, ends=None, lo=None, hi=None, div=False, log=False) -> tuple[np.ndarray, float, float]:
    """A 256 x 256 core layer: pixels without a correspondence in the no-correspondence tone."""
    g = d.grid(values)
    m = np.isfinite(g)
    out = np.zeros(g.shape + (3,), np.uint8)
    out[:] = NOCORR
    if not m.any():
        return out, 0.0, 0.0
    v = g[m]
    if log:
        v = np.log10(np.maximum(v, 1e-12))
    lo = float(np.quantile(v, 0.01)) if lo is None else lo
    hi = float(np.quantile(v, 0.99)) if hi is None else hi
    hi = hi if hi > lo else lo + 1e-12
    if div:
        out[m] = diverging(v / max(abs(lo), abs(hi)))
    else:
        out[m] = ramp((v - lo) / (hi - lo), ends)
    return out, lo, hi


def hatch_nocorr(img, x, y, size, d: Data) -> None:
    """Non-colour cue for 'no perfect correspondence': a light diagonal hatch."""
    if d.mask.all():
        return
    m = Image.fromarray((~d.mask).astype(np.uint8) * 255).resize((size, size), Image.NEAREST)
    full = Image.new("L", img.size, 0)
    full.paste(m, (int(x), int(y)))
    S.hatch(img, [x, y, x + size, y + size], (196, 192, 184), spacing=10, width=1, mask=full)


def histogram(img, x, y, w, h, values, edges, color, xlabel, log_count=False, ticks=None) -> None:
    dr = ImageDraw.Draw(img)
    dr.rectangle([x, y, x + w, y + h], fill=S.WHITE)
    v = np.asarray(values, np.float64)
    v = v[np.isfinite(v)]
    cn = np.histogram(np.clip(v, edges[0], edges[-1]), bins=edges)[0] if v.size else np.zeros(len(edges) - 1, int)
    top = max(1, int(cn.max()))
    pad_l, pad_b = 64, 42
    px0, py0, pw, ph = x + pad_l, y + 10, w - pad_l - 14, h - pad_b - 10
    for k in range(5):
        yy = py0 + ph - ph * k / 4
        dr.line([px0, yy, px0 + pw, yy], fill=S.GRID, width=1)
        caption(dr, px0 - 6, yy, f"{int(round(top * k / 4)):,}", size=13, fill=S.INK2, anchor="rm")
    nb = len(edges) - 1
    bw = pw / nb
    for b in range(nb):
        if cn[b] <= 0:
            continue
        hh = ph * cn[b] / top
        x0b = px0 + b * bw + 0.5
        dr.rectangle([x0b, py0 + ph - hh, x0b + max(1.0, bw - 1), py0 + ph], fill=color)
    dr.line([px0, py0 + ph, px0 + pw, py0 + ph], fill=S.INK2, width=1)
    for t in (ticks if ticks is not None else np.linspace(edges[0], edges[-1], 5)):
        xx = px0 + pw * (t[0] - edges[0]) / (edges[-1] - edges[0]) if isinstance(t, tuple) else \
            px0 + pw * (t - edges[0]) / (edges[-1] - edges[0])
        lab = t[1] if isinstance(t, tuple) else f"{t:.3g}"
        dr.line([xx, py0 + ph, xx, py0 + ph + 4], fill=S.INK2)
        caption(dr, xx, py0 + ph + 6, lab, size=13, fill=S.INK2, anchor="ma")
    caption(dr, px0 + pw / 2, y + h - 2, xlabel, size=13, fill=S.INK2, anchor="md")


def stat_lines(img, x, y, lines, size=SMALL, step=30, bold_first=False) -> None:
    dr = ImageDraw.Draw(img)
    for k, ln in enumerate(lines):
        caption(dr, x, y + step * k, ln, size=size, bold=bold_first and k == 0)


def fmt_q(q: dict | None, scale=1.0, unit="", nd=3, keys=("median", "p95", "max")) -> str:
    if not q:
        return "—"
    return ", ".join(f"{k} {q[k] * scale:.{nd}g}{unit}" for k in keys)


# ------------------------------------------------------------------ geometry helpers
def epipole_px(c: dict, side: int) -> tuple[float, float]:
    eye, other = c["eyes"][side], c["eyes"][1 - side]
    far = np.asarray(other["centre_h_m"], float) + 1e6 * (np.asarray(other["centre_h_m"], float)
                                                          - np.asarray(eye["centre_h_m"], float))
    uv, z = FG.project_h(eye, far[None])
    if z[0] <= 0:
        far = 2 * np.asarray(eye["centre_h_m"], float) - far
        uv, _ = FG.project_h(eye, far[None])
    return float(uv[0, 0]), float(uv[0, 1])


def raw_panel(d: Data, side: str, size: int, sliver: bool = False) -> Image.Image:
    """The saved raw L / R padded tangent RGB (ORACLE INPUT) with the nominal 12-degree core (dashed) and gaze."""
    w = d.c["image_size_wh"][0]
    k = size / w
    img = Image.fromarray(gamma(d.rgb["rgb_" + side])).resize((size, size), Image.BOX).convert("RGB")
    dr = ImageDraw.Draw(img)
    core = d.c["core_size"]
    o = (w - core) / 2 * k
    S.dashed_rect(dr, [o, o, o + core * k, o + core * k], S.WHITE, width=4, dash=10, gap=6)
    S.dashed_rect(dr, [o, o, o + core * k, o + core * k], S.INK, width=2, dash=10, gap=6)
    S.crosshair(dr, (w - 1) / 2 * k, (w - 1) / 2 * k, r=10, solid=True, width=2)
    if sliver:
        src = d.pre["eyes"][side]["raw_source_of_rectified_core_px"]
        x0, x1, y0, y1 = src["x"][0] * k, src["x"][1] * k, src["y"][0] * k, src["y"][1] * k
        pad = 6
        dr.rectangle([x0 - pad, y0 - pad, x1 + pad, y1 + pad], outline=S.WHITE, width=5)
        dr.rectangle([x0 - pad, y0 - pad, x1 + pad, y1 + pad], outline=S.INK, width=2)
        S.text(dr, (x0 - pad - 6, y1 + pad + 8), "AB1a rectified-core source", size=max(12, size // 40), plate=S.WHITE,
               anchor="ra")
    ex, ey = epipole_px(d.c, 0 if side == "L" else 1)
    if 0 <= ex * k <= size and 0 <= ey * k <= size:
        S.xmark(dr, ex * k, ey * k, r=7, color=S.WHITE, width=5)
        S.xmark(dr, ex * k, ey * k, r=7, color=S.INK, width=2)
    return img


class Chart:
    """Pixel mapping of the display chart (chart_u right, chart_v up), in degrees."""

    def __init__(self, x, y, w, h, u_lim, v_lim):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.u0, self.u1 = u_lim
        self.v0, self.v1 = v_lim

    def px(self, u_deg, v_deg):
        u, v = np.asarray(u_deg, float), np.asarray(v_deg, float)
        return (self.x + (u - self.u0) / (self.u1 - self.u0) * self.w,
                self.y + (self.v1 - v) / (self.v1 - self.v0) * self.h)

    def axes(self, dr, step=2.0, label=True):
        dr.rectangle([self.x, self.y, self.x + self.w, self.y + self.h], outline=S.INK2)
        for u in np.arange(math.ceil(self.u0 / step) * step, self.u1 + 1e-9, step):
            xx, _ = self.px(u, 0)
            dr.line([float(xx), self.y, float(xx), self.y + self.h], fill=S.GRID)
            if label:
                caption(dr, float(xx), self.y + self.h + 4, f"{u:+g}°" if u else "0", size=13, fill=S.INK2, anchor="ma")
        for v in np.arange(math.ceil(self.v0 / step) * step, self.v1 + 1e-9, step):
            _, yy = self.px(0, v)
            dr.line([self.x, float(yy), self.x + self.w, float(yy)], fill=S.GRID)
            if label:
                caption(dr, self.x - 6, float(yy), f"{v:+g}°" if v else "0", size=13, fill=S.INK2, anchor="rm")


def chart_limits(d: Data, pad=1.0) -> tuple[tuple, tuple]:
    cu, cv = np.degrees(d.rays["chart_u"]), np.degrees(d.rays["chart_v"])
    u0, u1 = float(cu.min()) - pad, float(cu.max()) + pad
    v0, v1 = float(np.nanmin(cv)) - pad, float(np.nanmax(cv)) + pad
    return (u0, u1), (v0, v1)


def chart_core(img, d: Data, x, y, w, h, colour="rgb", pole=True, title=None) -> Chart:
    """All 65,536 left raw-core rays splatted into the display chart (one dot per ray; no interpolation)."""
    (u0, u1), (v0, v1) = chart_limits(d)
    sc = min(w / (u1 - u0), h / (v1 - v0))          # px per degree, equal on both axes: every ray fits
    cu, cv = (u0 + u1) / 2, (v0 + v1) / 2
    ch = Chart(x, y, w, h, (cu - w / sc / 2, cu + w / sc / 2), (cv - h / sc / 2, cv + h / sc / 2))
    dr = ImageDraw.Draw(img)
    dr.rectangle([x, y, x + w, y + h], fill=S.WHITE)
    ch.axes(dr)
    u, v = ch.px(np.degrees(d.rays["chart_u"]).ravel(), np.degrees(d.rays["chart_v"]).ravel())
    col = gamma(d.core_rgb).reshape(-1, 3) if isinstance(colour, str) else colour.reshape(-1, 3)
    px = np.clip(np.rint(u).astype(int), x, x + w - 1)
    py = np.clip(np.rint(v).astype(int), y, y + h - 1)
    arr = np.asarray(img)
    arr = arr.copy()
    for dx in (0, 1):
        for dy in (0, 1):
            arr[np.clip(py + dy, y, y + h - 1), np.clip(px + dx, x, x + w - 1)] = col
    img.paste(Image.fromarray(arr), (0, 0))
    dr = ImageDraw.Draw(img)
    gx, gy = ch.px(0, 0)
    S.crosshair(dr, float(gx), float(gy), r=12, solid=True, width=2)
    if pole:
        # the +X pole sits at chart_u = -theta_g, chart_v = 0 (beyond the left edge): an arrow and its distance
        ax0, ay0 = ch.px(ch.u0 + 0.3, 0)
        dr.line([float(ax0) + 70, float(ay0), float(ax0) + 8, float(ay0)], fill=S.INK, width=3)
        dr.polygon([(float(ax0), float(ay0)), (float(ax0) + 14, float(ay0) - 8), (float(ax0) + 14, float(ay0) + 8)],
                   fill=S.INK)
        lc = d.gsum["left_core"]
        S.text(dr, (float(ax0) + 4, float(ay0) - 14), f"+X pole: θ = 0 at {np.degrees(d.tg):.1f}° from the gaze",
               size=14, plate=S.WHITE, anchor="ld")
        S.text(dr, (float(ax0) + 4, float(ay0) + 14), f"core's nearest ray {lc['min_angle_to_baseline_pole_deg']:.2f}°",
               size=14, plate=S.WHITE, anchor="la")
    caption(dr, x + w / 2, y + h + 26, "chart u = θ − θ_g  [deg]  (display chart only)", size=13, fill=S.INK2, anchor="ma")
    S.text(dr, (x + 6, y + 6), "chart v = sin θ_g · wrap(φ − φ_g)", size=13, fill=S.INK2, plate=S.WHITE)
    if title:
        caption(dr, x, y - 26, title, bold=True)
    return ch


def point_cloud(img, x, y, w, h, pts, col, view="top", extra=None) -> None:
    """Orthographic head-frame point cloud. top: X right / -Z up; side: -Z right / Y up."""
    sub = Image.new("RGB", (int(w), int(h)), S.WHITE)
    dr = ImageDraw.Draw(sub)
    if view == "top":
        P = lambda q: np.stack([q[..., 0], -q[..., 2]], -1)  # noqa: E731
        lbl = ("head X (right) [m]", "head −Z (forward) [m]")
    else:
        P = lambda q: np.stack([-q[..., 2], q[..., 1]], -1)  # noqa: E731
        lbl = ("head −Z (forward) [m]", "head Y (up) [m]")
    g = FG.gaze_direction(*extra["gaze"]) if extra else np.array([0, 0, -1.0])
    reach = float(np.quantile(np.linalg.norm(pts, axis=1), 0.99) * 1.1) if len(pts) else 5.0
    anchor = np.array([[0, 0, 0], g * reach, [reach * 0.25, 0, 0]])
    q = np.concatenate([P(anchor), P(pts)]) if len(pts) else P(anchor)
    lo, hi = q.min(0), q.max(0)
    span = float(max(hi - lo)) * 1.08 + 1e-6
    mid = (lo + hi) / 2
    pad = 36

    def to_px(v):
        v = (np.asarray(v) - mid) / span
        return pad + (v[..., 0] + 0.5) * (w - 2 * pad), h - pad - (v[..., 1] + 0.5) * (h - 2 * pad)
    for k in range(-30, 31):
        for axis in (0, 1):
            if axis == 0:
                a_, b_ = to_px(np.array([k, lo[1] - span]))
                c_, d_ = to_px(np.array([k, hi[1] + span]))
            else:
                a_, b_ = to_px(np.array([lo[0] - span, k]))
                c_, d_ = to_px(np.array([hi[0] + span, k]))
            dr.line([float(a_), float(b_), float(c_), float(d_)], fill=S.GRID, width=1)
    o = to_px(P(np.zeros(3)))
    e = to_px(P(g * reach))
    dr.line([float(o[0]), float(o[1]), float(e[0]), float(e[1])], fill=S.INK, width=2)
    S.text(dr, (float(e[0]), float(e[1])), "gaze #1", size=14, plate=S.WHITE, anchor="rb" if e[0] > w / 2 else "lb")
    xb = to_px(P(np.array([reach * 0.25, 0, 0])))
    S.dashed_line(dr, [(float(o[0]), float(o[1])), (float(xb[0]), float(xb[1]))], S.INK2, width=2, dash=6, gap=5)
    S.text(dr, (float(xb[0]), float(xb[1])), "+X baseline", size=13, fill=S.INK2, plate=S.WHITE, anchor="lm")
    if len(pts):
        px, py = to_px(P(pts))
        order = np.argsort(-pts[:, 1] if view == "top" else pts[:, 0], kind="stable")
        arr = np.asarray(sub).copy()
        xi, yi = np.clip(np.rint(px).astype(int), 0, int(w) - 2), np.clip(np.rint(py).astype(int), 0, int(h) - 2)
        for dx in (0, 1):
            for dy in (0, 1):
                arr[yi[order] + dy, xi[order] + dx] = col[order]
        sub = Image.fromarray(arr)
        dr = ImageDraw.Draw(sub)
    else:
        S.text(dr, (w / 2, h / 2), "0 reconstructed points", size=SMALL + 2, bold=True, plate=S.WHITE, anchor="mm")
    dr.ellipse([float(o[0]) - 4, float(o[1]) - 4, float(o[0]) + 4, float(o[1]) + 4], fill=S.INK)
    S.text(dr, (float(o[0]), float(o[1]) + 8), "eyes", size=13, fill=S.INK2, plate=S.WHITE, anchor="mt")
    caption(dr, w / 2, h - 6, lbl[0], size=13, fill=S.INK2, anchor="md")
    caption(dr, 6, 6, lbl[1] + "; 1 m grid", size=13, fill=S.INK2)
    dr.rectangle([0, 0, w - 1, h - 1], outline=S.INK2)
    img.paste(sub, (int(x), int(y)))


def pair_sample(d: Data, k=24) -> np.ndarray:
    """Deterministic representative matched pairs: an even raster-order subsample."""
    n = d.n
    if n == 0:
        return np.zeros(0, int)
    return np.unique(np.linspace(0, n - 1, min(k, n)).round().astype(int))


def pairs_chart(img, d: Data, x, y, w, h, k=24, mag=None) -> None:
    """Representative matched ray pairs in the display chart: left ray (filled dot) to right ray (ring), with the
    angular disparity magnified for legibility (the magnification is stated); equal chart_v = equal phi."""
    ch = chart_core(img, d, x, y, w, h, colour=np.full((SP.CORE_SIZE, SP.CORE_SIZE, 3), 232, np.uint8), pole=False)
    dr = ImageDraw.Draw(img)
    idx = pair_sample(d, k)
    if not len(idx):
        statement(img, x, y, w, h, ["0 perfect correspondences", "no ray pairs"])
        return
    dth = np.degrees(d.res["delta_theta"][idx])
    m = mag or float(max(1, round(1.0 / max(1e-9, float(np.median(np.abs(dth)))))))
    for i in idx:
        ul, vl = np.degrees(d.res["chart_u_L"][i]), np.degrees(d.res["chart_v_L"][i])
        ur, vr = np.degrees(d.res["chart_u_R"][i]), np.degrees(d.res["chart_v_R"][i])
        x0, y0 = ch.px(ul, vl)
        x1, y1 = ch.px(ul + (ur - ul) * m, vl + (vr - vl) * m)
        if not (x <= min(x0, x1) and max(x0, x1) <= x + w and y <= min(y0, y1) and max(y0, y1) <= y + h):
            continue
        dr.line([float(x0), float(y0), float(x1), float(y1)], fill=S.INK2, width=2)
        dr.ellipse([float(x0) - 4, float(y0) - 4, float(x0) + 4, float(y0) + 4], fill=S.OI_BLUE)
        dr.ellipse([float(x1) - 5, float(y1) - 5, float(x1) + 5, float(y1) + 5], outline=S.OI_VERM, width=2)
    S.text(dr, (x + w - 8, y + h - 8), f"{len(idx)} pairs; Δθ magnified ×{m:g}; ● left ray, ○ right ray",
           size=14, plate=S.WHITE, anchor="rd")


def comparison_bars(img, x, y, w, d: Data) -> None:
    dr = ImageDraw.Draw(img)
    a = d.ev["ab1a_comparison"]
    p, s = a["ab1a_planar_rectified"], a["ab1b_spherical_raw_core"]
    n = s["core_pixels"]
    rows = [("AB1a planar rectified core: reference-valid", p["reference_valid"], True),
            ("AB1a planar rectified core: natural-valid", p["natural_valid"], True),
            ("AB1b raw-core rays represented", s["raw_core_rays_represented"], False),
            ("AB1b raw-core perfect correspondences", s["perfect_correspondences"], False),
            ("AB1b triangulated (spherical epipolar)", s["triangulated"], False)]
    lab_w, bw, rh = 470, w - 470 - 130, 34
    for k, (lab, v, old) in enumerate(rows):
        yy = y + k * (rh + 8)
        caption(dr, x + lab_w - 10, yy + rh / 2, lab, size=15, anchor="rm")
        dr.rectangle([x + lab_w, yy, x + lab_w + bw, yy + rh], fill=(240, 239, 235))
        if v:
            dr.rectangle([x + lab_w, yy, x + lab_w + max(3.0, bw * v / n), yy + rh], fill=S.INK2 if not old else S.INK)
        if old:
            S.hatch(img, [x + lab_w, yy, x + lab_w + bw, yy + rh], (205, 200, 190), spacing=9, width=1)
            dr = ImageDraw.Draw(img)
        caption(dr, x + lab_w + bw + 10, yy + rh / 2, f"{v:,} / {n:,}", size=15, bold=True, anchor="lm")


# ------------------------------------------------------------------ figures
def raw_foveal_core(d: Data) -> Image.Image:
    W, H = 2100, 1060
    img = Image.new("RGB", (W, H), S.SURFACE)
    header(img, "AB1b — the same observation: the saved AB1a raw pair and its nominal 12° raw core",
           ["No new render: the accepted AB1a gaze-#1 pair (+76.75°, +7.75°) is re-analysed.  Dashed: the central "
            "256 × 256 raw core (x, y = 192..447) of the 640 × 640 padded raster.  x: the other eye's epipole."], [ORA, DER])
    s = 620
    for i, side in enumerate(("L", "R")):
        xx = 40 + i * (s + 30)
        img.paste(raw_panel(d, side, s), (xx, 150))
        frame(ImageDraw.Draw(img), xx, 150, s, s)
        caption(ImageDraw.Draw(img), xx, 150 + s + 6, f"raw {side} 640 × 640 (29.4°); dashed: nominal 12° core", size=14,
                fill=S.INK2)
    xx = 40 + 2 * (s + 30) + 20
    img.paste(nearest(gamma(d.core_rgb), s), (xx, 150))
    frame(ImageDraw.Draw(img), xx, 150, s, s)
    caption(ImageDraw.Draw(img), xx, 150 + s + 6, "left raw core 256 × 256: the AB1b measurement domain (65,536 rays)",
            size=14, fill=S.INK2)
    lc = d.gsum["left_core"]
    stat_lines(img, 40, 150 + s + 50, [
        f"gaze #1 yaw {d.yaw:+.2f}°, pitch {d.pitch:+.2f}°; θ_g = {d.gsum['theta_g_deg']:.3f}° from the +X baseline; "
        f"φ_g = {d.gsum['phi_g_deg']:.3f}°",
        f"left raw-core rays: {lc['rays']:,} (finite {lc['finite']:,}, pole-singular {lc['pole_singular']}); θ "
        f"{lc['theta_deg']['min']:.2f}..{lc['theta_deg']['max']:.2f}°; nearest approach to the baseline pole "
        f"{lc['min_angle_to_baseline_pole_deg']:.2f}°",
        "The right match may use the whole padded right raster (search margin); it need not fall in the right 256 core.",
        NOT_STATEMENT])
    return img


def spherical_epipolar_core(d: Data) -> Image.Image:
    W, H = 2300, 1240
    img = Image.new("RGB", (W, H), S.SURFACE)
    header(img, "AB1b — spherical epipolar representation of the whole raw core (calibration only)",
           ["Every one of the 65,536 left raw-core sensor rays, expressed as θ (from +X, the baseline) and φ = atan2(d_y, −d_z) "
            "(the epipolar plane), drawn in the gaze-centered display chart.  RGB carried for visualization only."],
           [DER, ORA])
    chart_core(img, d, 120, 190, 900, 900, title="all 65,536 raw-core rays in the display chart (one dot per ray)")
    s = 380
    x0 = 1120
    lc = d.gsum["left_core"]
    th = np.degrees(d.rays["theta"])
    ph = np.degrees(d.rays["phi"])
    lev = d.rays["leverage"]
    for k, (arr, ends, lab, f) in enumerate([(th, RANGE_RAMP, "θ [deg] (from +X)", "{:.1f}"),
                                             (ph, DISP_RAMP, "φ [deg] (epipolar plane)", "{:.1f}"),
                                             (lev, COND_RAMP, "leverage sin θ", "{:.3f}")]):
        xx = x0 + (k % 2) * (s + 80)
        yy = 190 + (k // 2) * (s + 120)
        lo, hi = float(arr.min()), float(arr.max())
        img.paste(nearest(ramp((arr - lo) / (hi - lo), ends), s), (xx, yy))
        frame(ImageDraw.Draw(img), xx, yy, s, s)
        colorbar(img, xx, yy + s + 30, s, 14, lo, hi, ends, label=lab, fmt=f)
        caption(ImageDraw.Draw(img), xx, yy - 26, lab + " over the raw core (image layout)", size=15, bold=True)
    xx, yy = x0 + (s + 80), 190 + (s + 120)
    stat_lines(img, xx, yy, [
        "calibration-only raw-core geometry",
        f"rays {lc['rays']:,}; finite {lc['finite']:,}",
        f"pole-singular {lc['pole_singular']}",
        f"θ min / median / max",
        f"  {lc['theta_deg']['min']:.3f} / {lc['theta_deg']['median']:.3f} / {lc['theta_deg']['max']:.3f}°",
        f"nearest pole {lc['nearest_pole']}: {lc['min_angle_to_baseline_pole_deg']:.3f}°",
        f"φ {lc['phi_deg']['min']:.2f}..{lc['phi_deg']['max']:.2f}°",
        f"chart u {np.degrees(lc['chart_u_rad']['min']):.2f}..{np.degrees(lc['chart_u_rad']['max']):.2f}°",
        f"chart v {np.degrees(lc['chart_v_rad']['min']):.2f}..{np.degrees(lc['chart_v_rad']['max']):.2f}°",
        f"leverage {lc['leverage_sin_theta']['min']:.3f} / {lc['leverage_sin_theta']['median']:.3f} / "
        f"{lc['leverage_sin_theta']['max']:.3f}"], size=16, step=29, bold_first=True)
    return img


def perfect_correspondences(d: Data) -> Image.Image:
    W, H = 2300, 1180
    img = Image.new("RGB", (W, H), S.SURFACE)
    header(img, "AB1b — perfect / oracle correspondence (Position and Object Index used here only)",
           ["Each left raw-core pixel's Position is projected through the right raw camera; kept when the nearest right "
            "pixel sees the same instance.  The geometry stage receives only (row, col, uv_L, uv_R): truth stripped."],
           [ORA, DER])
    s = 560
    lay = np.zeros((SP.CORE_SIZE, SP.CORE_SIZE, 3), np.uint8)
    lay[:] = NOCORR
    g = gamma(d.core_rgb)
    lay[d.mask] = g[d.mask]
    img.paste(nearest(lay, s), (40, 170))
    hatch_nocorr(img, 40, 170, s, d)
    frame(ImageDraw.Draw(img), 40, 170, s, s)
    caption(ImageDraw.Draw(img), 40, 170 + s + 6, f"left raw core: RGB where a perfect correspondence exists "
            f"({d.n:,}); hatched: none", size=14, fill=S.INK2)
    # right raster: where the matches land
    x1 = 40 + s + 40
    k = s / SP.RAW_SIZE
    rimg = Image.fromarray(gamma(d.rgb["rgb_R"])).resize((s, s), Image.BOX).convert("RGB")
    rimg = Image.blend(rimg, Image.new("RGB", (s, s), (255, 255, 255)), 0.55)
    arr = np.asarray(rimg).copy()
    if d.n:
        u = np.clip(np.rint(d.prod["uv_R"][:, 0] * k).astype(int), 0, s - 1)
        v = np.clip(np.rint(d.prod["uv_R"][:, 1] * k).astype(int), 0, s - 1)
        arr[v, u] = S.OI_BLUE
    rimg = Image.fromarray(arr)
    dr = ImageDraw.Draw(rimg)
    o = SP.CORE_ORIGIN * k
    S.dashed_rect(dr, [o, o, o + SP.CORE_SIZE * k, o + SP.CORE_SIZE * k], S.INK, width=2, dash=10, gap=6)
    img.paste(rimg, (x1, 170))
    frame(ImageDraw.Draw(img), x1, 170, s, s)
    rm = d.osum["right_margin"]
    caption(ImageDraw.Draw(img), x1, 170 + s + 6, f"right raw raster: matched uv_R (blue); dashed: right nominal core; "
            f"outside it: {rm['outside_right_nominal_core']:,}", size=14, fill=S.INK2)
    # attrition
    dr = ImageDraw.Draw(img)
    x2 = x1 + s + 50
    caption(dr, x2, 170, "attrition (sequential, descriptive; no target count)", bold=True)
    n0 = d.osum["left_core_pixels"]
    bw = W - x2 - 60 - 150
    for i, st in enumerate(d.osum["attrition"]):
        yy = 214 + i * 64
        caption(dr, x2, yy, st["step"], size=15)
        dr.rectangle([x2, yy + 24, x2 + bw, yy + 50], fill=(240, 239, 235))
        if st["remaining"]:
            dr.rectangle([x2, yy + 24, x2 + max(3.0, bw * st["remaining"] / n0), yy + 50], fill=S.INK2)
        caption(dr, x2 + bw + 10, yy + 37, f"{st['remaining']:,}", size=15, bold=True, anchor="lm")
    ex = d.osum["excluded"]
    stat_lines(img, x2, 214 + 7 * 64 + 10, [
        f"no finite hit {ex['no_finite_hit']:,}; hit with instance 0 {ex['hit_with_instance_0']:,}",
        f"not right-projectable {ex['not_right_projectable']:,}; outside padded raster {ex['outside_padded_right_raster']:,}",
        f"different right instance (half-occlusion) {ex['different_right_instance']:,}",
        f"u_R {rm['u_R_min']:.1f}..{rm['u_R_max']:.1f}, v_R {rm['v_R_min']:.1f}..{rm['v_R_max']:.1f} (continuous)"
        if rm["u_R_min"] is not None else "no match"], size=15, step=28)
    return img


def epipolar_residual(d: Data) -> Image.Image:
    W, H = 1900, 900
    img = Image.new("RGB", (W, H), S.SURFACE)
    q = d.gsum["distributions"]["abs_phi_residual_rad"]
    header(img, "AB1b — epipolar consistency: |φ_R − φ_L| for every perfect correspondence",
           ["Corresponding rays should share the epipolar plane φ.  The residual is wrapped to (−π, π].  "
            f"|φ residual| {fmt_q(q, 1, ' rad')}."], [DER])
    s = 600
    vals = np.abs(d.res["phi_residual"])
    lay, lo, hi = layer(d, vals, ERR_RAMP, lo=0.0)
    img.paste(nearest(lay, s), (40, 170))
    hatch_nocorr(img, 40, 170, s, d)
    frame(ImageDraw.Draw(img), 40, 170, s, s)
    colorbar(img, 40, 170 + s + 40, s, 14, lo, hi, ERR_RAMP, label="|φ residual| [rad] over the left raw core",
             fmt="{:.2e}")
    if d.n:
        top = float(np.quantile(vals, 0.999)) * 1.05 + 1e-15
        histogram(img, 700, 170, W - 760, 420, vals, np.linspace(0, top, 61), S.INK2, "|φ_R − φ_L| [rad]",
                  ticks=[(t, f"{t:.1e}") for t in np.linspace(0, top, 5)])
    stat_lines(img, 700, 640, [f"pairs {d.n:,}", f"|φ residual|: {fmt_q(q, 1, ' rad', keys=('median', 'p95', 'p99', 'max'))}",
                               "equivalent pixels at the core: residual × f × sin θ ≈ "
                               + (f"{q['median'] * d.gsum['focal_px'] * math.sin(d.tg):.2e} px (median)" if q else "—")])
    return img


def angular_disparity(d: Data) -> Image.Image:
    W, H = 1900, 900
    img = Image.new("RGB", (W, H), S.SURFACE)
    q = d.gsum["distributions"]["delta_theta_rad"]
    k = d.gsum["counts"]
    header(img, "AB1b — angular binocular disparity δθ = θ_R − θ_L",
           [f"δθ > 0 for {k['delta_theta_positive']:,}, = 0 for {k['delta_theta_zero']:,}, < 0 for "
            f"{k['delta_theta_negative']:,} of {k['correspondences']:,} pairs.  δθ (mrad): "
            + (f"p05 {q['p05'] * 1e3:.3f}, median {q['median'] * 1e3:.3f}, p95 {q['p95'] * 1e3:.3f}" if q else "—")], [DER])
    s = 600
    vals = d.res["delta_theta"] * 1e3
    lay, lo, hi = layer(d, vals, DISP_RAMP)
    img.paste(nearest(lay, s), (40, 170))
    hatch_nocorr(img, 40, 170, s, d)
    frame(ImageDraw.Draw(img), 40, 170, s, s)
    colorbar(img, 40, 170 + s + 40, s, 14, lo, hi, DISP_RAMP, label="δθ [mrad] over the left raw core", fmt="{:.2f}")
    if d.n:
        a, b = float(np.quantile(vals, 0.001)), float(np.quantile(vals, 0.999))
        histogram(img, 700, 170, W - 760, 420, vals, np.linspace(a, b + 1e-9, 61), tuple(int(v) for v in DISP_RAMP[1]),
                  "δθ [mrad]")
    stat_lines(img, 700, 640, ["δθ is the angle between the rays measured within their shared epipolar plane;",
                               "larger δθ = nearer surface.  The sign is recorded and validated for the canonical scene."])
    return img


def conditioning(d: Data) -> Image.Image:
    W, H = 2300, 1060
    img = Image.new("RGB", (W, H), S.SURFACE)
    dd = d.gsum["distributions"]
    header(img, "AB1b — how poorly conditioned is gaze #1?  (descriptive; nothing is rejected)",
           [f"ray intersection angle γ, κ = 1/|sin γ|, and the first-order range change per pixel-equivalent angle "
            f"(B sin θ_L / sin² δθ / f).  B⊥ at this gaze is about {d.c['ipd_m'] * math.sin(d.tg) * 1000:.1f} mm."], [DER])
    s = 520
    for i, (key, vals, ends, lab, fmt, logs) in enumerate([
            ("gamma", d.res["gamma"] * 1e3, COND_RAMP, "γ [mrad]", "{:.2f}", False),
            ("kappa", d.res["kappa"], ERR_RAMP, "κ = 1/|sin γ|", "{:.0f}", False),
            ("per_px", d.res["range_per_px"], RANGE_RAMP, "range per px-equivalent [m]", "{:.3f}", False)]):
        xx = 40 + i * (s + 230)
        lay, lo, hi = layer(d, vals, ends, log=logs)
        img.paste(nearest(lay, s), (xx, 170))
        hatch_nocorr(img, xx, 170, s, d)
        frame(ImageDraw.Draw(img), xx, 170, s, s)
        colorbar(img, xx, 170 + s + 40, s, 14, lo, hi, ends, label=lab, fmt=fmt)
    stat_lines(img, 40, 170 + s + 100, [
        f"γ: {fmt_q(dd['ray_angle_gamma_rad'], 1e3, ' mrad', keys=('min', 'median', 'p95', 'max'))}",
        f"κ: {fmt_q(dd['kappa'], 1, '', keys=('min', 'median', 'p95', 'max'))}",
        f"range per pixel-equivalent angle: {fmt_q(dd['range_per_px_m'], 1, ' m', keys=('min', 'median', 'p95', 'max'))}",
        f"reconstructed left range: {fmt_q(dd['range_L_m'], 1, ' m', keys=('min', 'median', 'p95', 'max'))}"],
        size=17, step=32)
    return img


def reconstructed_point_cloud(d: Data) -> Image.Image:
    W, H = 2200, 1100
    img = Image.new("RGB", (W, H), S.SURFACE)
    header(img, "AB1b — truth-free spherical epipolar reconstruction P_epi (RGB-coloured)",
           [f"{int(d.ve.sum()):,} points triangulated from (θ_L, θ_R, φ̄) alone: no Position, no Object Index.  "
            "Head frame, orthographic, 1 m grid."], [DER])
    rows, cols = d.res["left_core_row"][d.ve], d.res["left_core_col"][d.ve]
    col = gamma(d.core_rgb[rows, cols]) if len(rows) else np.zeros((0, 3), np.uint8)
    pts = d.res["P_epi"][d.ve]
    point_cloud(img, 40, 150, 1040, 900, pts, col, "top", {"gaze": (d.yaw, d.pitch)})
    point_cloud(img, 1120, 150, 1040, 900, pts, col, "side", {"gaze": (d.yaw, d.pitch)})
    caption(ImageDraw.Draw(img), 40, 1060, "top view", size=14, fill=S.INK2)
    caption(ImageDraw.Draw(img), 1120, 1060, "projection onto head (−Z, Y): seen along the +X baseline, nearly face-on to "
            "the fixation", size=14, fill=S.INK2)
    return img


def triangulation_error(d: Data) -> Image.Image:
    W, H = 2300, 860
    img = Image.new("RGB", (W, H), S.SURFACE)
    ee, er = d.ev["epipolar_vs_truth"], d.ev["ray_ray_vs_truth"]
    header(img, "AB1b — post-freeze reference evaluation: P_epi and P_ray against Position (second role of Position)",
           ["Evaluation opened Position only after the geometry freeze verified; it changes nothing.  Pixels without a "
            "perfect correspondence are hatched."], [REF, DER])
    s = 520
    e3 = d.evr["error_3d_epi_m"] * 1e3
    lay, lo, hi = layer(d, e3, ERR_RAMP, lo=0.0)
    img.paste(nearest(lay, s), (40, 170))
    hatch_nocorr(img, 40, 170, s, d)
    frame(ImageDraw.Draw(img), 40, 170, s, s)
    colorbar(img, 40, 170 + s + 40, s, 14, lo, hi, ERR_RAMP, label="|P_epi − P_truth| [mm]", fmt="{:.3f}")
    rad = d.evr["radial_signed_epi_m"] * 1e3
    lim = float(np.quantile(np.abs(rad[np.isfinite(rad)]), 0.99)) if np.isfinite(rad).any() else 1.0
    lay, _, _ = layer(d, rad, lo=-lim, hi=lim, div=True)
    img.paste(nearest(lay, s), (40 + s + 60, 170))
    hatch_nocorr(img, 40 + s + 60, 170, s, d)
    frame(ImageDraw.Draw(img), 40 + s + 60, 170, s, s)
    colorbar(img, 40 + s + 60, 170 + s + 40, s, 14, -lim, lim, div=True, label="signed radial error [mm]", fmt="{:.3f}")
    x2 = 40 + 2 * (s + 60)
    if d.n:
        top = float(np.quantile(e3[np.isfinite(e3)], 0.999)) * 1.05 + 1e-12
        histogram(img, x2, 170, W - x2 - 40, 380, e3, np.linspace(0, top, 61), tuple(int(v) for v in ERR_RAMP[1]),
                  "|P_epi − P_truth| [mm]")
    fe = ee["fraction_3d_within_m"] or {}
    stat_lines(img, x2, 590, [
        f"P_epi, {ee['pairs']:,} pairs: 3-D error (mm) "
        f"{fmt_q(ee['error_3d_m'], 1e3, '', keys=('median', 'p95', 'p99', 'max'))}",
        f"  |radial| (mm) {fmt_q(ee['radial_abs_m'], 1e3, '', keys=('median', 'p95', 'p99', 'max'))}",
        "  within 1 / 5 / 10 / 25 mm: " + " / ".join(f"{fe.get(k, 0):.4f}" for k in ("0.001", "0.005", "0.010", "0.025")),
        f"P_ray, {er['pairs']:,} pairs: 3-D error (mm) "
        f"{fmt_q(er['error_3d_m'], 1e3, '', keys=('median', 'p95', 'p99', 'max'))}",
        f"|P_epi − P_ray| (m): {fmt_q(d.gsum['distributions']['epi_ray_difference_m'], 1, '', keys=('median', 'p95', 'max'))}",
        f"reprojection of P_epi (px): left {fmt_q(d.ev['reprojection_px']['left'], 1, '', keys=('median', 'max'))}; "
        f"right {fmt_q(d.ev['reprojection_px']['right'], 1, '', keys=('median', 'max'))}"], size=16, step=30)
    return img


def planar_vs_spherical(d: Data) -> Image.Image:
    W, H = 2300, 1200
    img = Image.new("RGB", (W, H), S.SURFACE)
    a = d.ev["ab1a_comparison"]
    p = a["ab1a_planar_rectified"]
    header(img, "AB1b — what planar rectification lost, and what the spherical representation keeps",
           ["Left: the AB1a planar rectified core was sourced from a tiny raw sliver near the epipole (solid box), "
            f"{p['rectified_core_centre_from_gaze_deg']:.2f}° from the gaze.  Right: AB1b keeps every raw-core ray.  "
            "The AB1a result is read post-freeze, descriptively."], [REF, DER])
    s = 640
    img.paste(raw_panel(d, "L", s, sliver=True), (40, 170))
    frame(ImageDraw.Draw(img), 40, 170, s, s)
    src = p["rectified_core_raw_source_px_L"]
    caption(ImageDraw.Draw(img), 40, 170 + s + 6, f"raw L: AB1a rectified-core source x {src['x'][0]:.2f}–{src['x'][1]:.2f}, "
            f"y {src['y'][0]:.2f}–{src['y'][1]:.2f} px (solid box)", size=14, fill=S.INK2)
    chart_core(img, d, 40 + s + 90, 170, 700, s, title=None)
    caption(ImageDraw.Draw(img), 40 + s + 90, 170 + s + 50, "AB1b: all 65,536 raw-core rays in the display chart",
            size=14, fill=S.INK2)
    x3 = 40 + s + 90 + 700 + 60
    stat_lines(img, x3, 180, [
        "AB1a (planar, accepted, MEASURED)",
        f"rectified-core pixels from the raw core: {p['rectified_core_pixels_from_nominal_raw_core']:,}",
        f"core centre {p['rectified_core_centre_from_gaze_deg']:.2f}° from gaze,",
        f"  {p['rectified_core_centre_from_baseline_deg']:.2f}° from the baseline",
        f"natural valid {p['natural_valid']:,} / {p['core_pixels']:,}",
        f"reference valid {p['reference_valid']:,} / {p['core_pixels']:,}",
        "",
        "AB1b (spherical, this run)",
        f"raw-core rays {a['ab1b_spherical_raw_core']['raw_core_rays_represented']:,} / 65,536",
        f"perfect correspondences {a['ab1b_spherical_raw_core']['perfect_correspondences']:,}",
        f"triangulated {a['ab1b_spherical_raw_core']['triangulated']:,}"], size=16, step=30, bold_first=True)
    comparison_bars(img, 40, 170 + s + 110, W - 80, d)
    return img


def overview(d: Data) -> Image.Image:
    W, H = 2400, 2420
    img = Image.new("RGB", (W, H), S.SURFACE)
    header(img, "Active Bootstrap-1b — spherical epipolar geometry at gaze #1",
           ["Does spherical epipolar geometry preserve and reconstruct the foveal region that planar rectification lost?  "
            "Correspondence is held perfect on purpose: this tests REPRESENTATION only.", NOT_STATEMENT], [ORA, DER, REF])
    ax, aw = 40, W - 80
    # A
    ay, ah = 170, 560
    region(img, ax, ay, aw, ah, "A", "SAME OBSERVATION (saved AB1a gaze-#1 pair; no new render)", [ORA, DER])
    s = 440
    for i, side in enumerate(("L", "R")):
        xx = ax + 20 + i * (s + 24)
        img.paste(raw_panel(d, side, s), (xx, ay + 70))
        frame(ImageDraw.Draw(img), xx, ay + 70, s, s)
        caption(ImageDraw.Draw(img), xx, ay + 70 + s + 4, f"raw {side} 640 × 640; dashed: nominal 12° core", size=13,
                fill=S.INK2)
    tx = ax + 20 + 2 * (s + 24) + 20
    lc = d.gsum["left_core"]
    stat_lines(img, tx, ay + 80, [
        "the accepted AB1a observation, re-analysed",
        f"frozen NB1c RGB gaze #1: yaw {d.yaw:+.2f}°, pitch {d.pitch:+.2f}°",
        f"gaze θ_g = {d.gsum['theta_g_deg']:.3f}° from the +X eye baseline",
        f"leverage sin θ_g = {math.sin(d.tg):.4f}; B⊥ = {d.c['ipd_m'] * math.sin(d.tg) * 1000:.2f} mm (forward: 63 mm)",
        f"IPD {d.c['ipd_m'] * 1000:.0f} mm; raw 640 × 640, core 256 × 256 (12°)",
        "no Blender, no render, no new gaze, no controller",
        "",
        "measurement domain: the RAW left 256 × 256 core",
        "right matches may use the padded 640 × 640 raster",
        "no rectified image, no cv2.stereoRectify, no crop"], size=17, step=34, bold_first=True)
    # B
    by, bh = ay + ah + 24, 620
    region(img, ax, by, aw, bh, "B", "SPHERICAL EPIPOLAR REPRESENTATION (calibration only)", [DER, ORA])
    chart_core(img, d, ax + 110, by + 80, 760, 470)
    tx = ax + 110 + 760 + 60
    stat_lines(img, tx, by + 80, [
        "all 65,536 left raw-core rays, one dot each",
        "θ = atan2(√(d_y² + d_z²), d_x)  (from +X)",
        "φ = atan2(d_y, −d_z)  (epipolar plane about X)",
        f"rays finite {lc['finite']:,}; pole-singular {lc['pole_singular']}",
        f"θ {lc['theta_deg']['min']:.2f}..{lc['theta_deg']['max']:.2f}°; nearest pole {lc['min_angle_to_baseline_pole_deg']:.2f}°",
        f"leverage sin θ {lc['leverage_sin_theta']['min']:.3f}..{lc['leverage_sin_theta']['max']:.3f}",
        "the foveal support stays finite and two-dimensional",
        "(AB1a planar core: a 0.09 × 4.8 raw-px sliver)",
        "display chart only: not a matcher raster"], size=17, step=34)
    # C
    cy, chh = by + bh + 24, 600
    region(img, ax, cy, aw, chh, "C", "PERFECT CORRESPONDENCE / TRIANGULATION (truth-free geometry)", [ORA, DER])
    pairs_chart(img, d, ax + 110, cy + 80, 640, 440)
    dd = d.gsum["distributions"]
    q1, q2 = dd["abs_phi_residual_rad"], dd["delta_theta_rad"]
    tx = ax + 110 + 640 + 30
    stat_lines(img, tx, cy + 80, [
        f"perfect correspondences {d.n:,} / 65,536",
        f"triangulated {int(d.ve.sum()):,}",
        "|φ_R − φ_L| (rad)",
        f"  {fmt_q(q1, 1, '', keys=('median', 'p95', 'max'))}",
        "δθ = θ_R − θ_L (mrad)",
        f"  {fmt_q(q2, 1e3, '', keys=('p05', 'median', 'p95'))}",
        f"δθ > 0: {d.gsum['counts']['delta_theta_positive']:,}",
        "ρ = B / (cot θ_L − cot θ_R)",
        "x = −B/2 + ρ cot θ_L; y, z from φ̄"], size=16, step=31)
    rows, cols = d.res["left_core_row"][d.ve], d.res["left_core_col"][d.ve]
    col = gamma(d.core_rgb[rows, cols]) if len(rows) else np.zeros((0, 3), np.uint8)
    point_cloud(img, ax + aw - 20 - 720, cy + 70, 720, 500, d.res["P_epi"][d.ve], col, "top", {"gaze": (d.yaw, d.pitch)})
    # D
    dy0 = cy + chh + 24
    dh = H - dy0 - 30
    region(img, ax, dy0, aw, dh, "D", "REFERENCE / COMPARISON (post-freeze)", [REF])
    ee = d.ev["epipolar_vs_truth"]
    fe = ee["fraction_3d_within_m"] or {}
    stat_lines(img, ax + 30, dy0 + 76, [
        "P_epi vs Position (opened after the geometry freeze)",
        f"3-D error (mm): {fmt_q(ee['error_3d_m'], 1e3, '', keys=('median', 'p95', 'p99', 'max'))}",
        f"|radial| (mm): {fmt_q(ee['radial_abs_m'], 1e3, '', keys=('median', 'p95', 'max'))}",
        "within 1 / 5 / 10 / 25 mm: " + " / ".join(f"{fe.get(k, 0):.3f}" for k in ("0.001", "0.005", "0.010", "0.025")),
        f"conditioning κ: {fmt_q(dd['kappa'], 1, '', keys=('median', 'p95'))}; γ (mrad): "
        f"{fmt_q(dd['ray_angle_gamma_rad'], 1e3, '', keys=('median', 'p95'))}",
        f"range per px-equivalent (m): {fmt_q(dd['range_per_px_m'], 1, '', keys=('median', 'p95'))}"],
        size=17, step=34, bold_first=True)
    comparison_bars(img, ax + 1060, dy0 + 80, aw - 1080, d)
    return img


def render_all(run: Path) -> tuple[dict, Data]:
    d = Data(run)
    figs = {"overview.png": overview(d), "raw-foveal-core.png": raw_foveal_core(d),
            "spherical-epipolar-core.png": spherical_epipolar_core(d),
            "perfect-correspondences.png": perfect_correspondences(d), "epipolar-residual.png": epipolar_residual(d),
            "angular-disparity.png": angular_disparity(d), "conditioning.png": conditioning(d),
            "reconstructed-point-cloud.png": reconstructed_point_cloud(d),
            "triangulation-error.png": triangulation_error(d), "planar-vs-spherical.png": planar_vs_spherical(d)}
    return figs, d


def visualize(run: Path, vis: Path) -> dict:
    vis.mkdir(parents=True, exist_ok=True)
    figs, d = render_all(run)
    out = {}
    for name in FIGURES:
        (vis / name).write_bytes(png_bytes(figs[name]))
        out[name] = {"sha256": sha256(vis / name), "badges": BADGES[name], "size": list(figs[name].size)}
    man = {"schema": "AB1b-visuals-manifest-v1", "figures": out, "sources": d.sources,
           "regenerate": ".venv/bin/python tools/active_bootstrap/ab1b_run.py visualize --run RUN --visuals VIS",
           "style": "Visual Language 1 (tools/visual_language/style.py)", "fonts": S.font_hashes(),
           "statement": NOT_STATEMENT}
    (vis / "visuals-manifest.json").write_text(json.dumps(man, indent=1, sort_keys=True) + "\n")
    print(f"[ab1b] visualize: {len(out)} figures -> {vis}")
    return man
