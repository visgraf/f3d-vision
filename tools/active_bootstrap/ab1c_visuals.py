"""Active Bootstrap-1c: the persistent human-facing figures of safe-forward planar vs spherical geometry.

Contract: docs/active-bootstrap/ab1c-safe-forward-planar-vs-spherical-contract.md, section 15.  Reads the AB1c run
(selection, observations, oracle, spherical, planar, comparison, evaluation), the frozen NB1c attention raster and, for
display only, the coarse NB1c RGB proxy.  Draws with Visual Language 1 (``style.py``) and the accepted AB1b figure helpers
(read-only).

Truth classes (text badges, never colour alone): ORACLE INPUT (the rendered RGB; Position / Object Index as the oracle
uses them; the coarse RGB proxy), DERIVED (selection geometry, rays, correspondences, both reconstructions, the
comparison, conditioning), REFERENCE / EVALUATION (Position when scoring).  Nothing is CONTROLLER-TIME.  Selection panels
carry the caption label EXPERIMENT SELECTION (dashed outline): chosen by the experiment's predeclared rule, not by a
controller; it is not a new Visual Language 1 class.  Glyphs: numbered solid crosshair = a frozen AB1c gaze; dashed ring
= its D_MIN exclusion; dashed square = the nominal 12-degree raw core; solid outline = the raw source of the fixed central
rectified (planar) core; + = head forward (-Z); hatch = outside the SAFE-FORWARD envelope / no correspondence.
Deterministic: the checker regenerates every PNG byte-identically.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
for _p in (HERE, TOOLS, TOOLS / "classroom_oracle", TOOLS / "visual_language", TOOLS / "natural_bootstrap"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import ab1b_visuals as BV  # noqa: E402  (accepted AB1b figure helpers, read-only)
import ab1c_planar as PL  # noqa: E402
import ab1c_spec as SP  # noqa: E402
import fsg_geometry as FG  # noqa: E402  (accepted, read-only)
import style as S  # noqa: E402  (Visual Language 1, read-only)

ORA, DER, REF = SP.TRUTH_ORACLE, SP.TRUTH_DERIVED, SP.TRUTH_REFERENCE
SMALL = 17
FIGURES = ["overview.png", "safe-forward-selection.png", "binocular-observations.png", "planar-support.png",
           "spherical-support.png", "common-correspondences.png", "planar-vs-spherical-difference.png",
           "paired-reconstruction.png", "truth-error.png", "conditioning.png"]
BADGES = {"overview.png": [ORA, DER, REF], "safe-forward-selection.png": [ORA, DER],
          "binocular-observations.png": [ORA], "planar-support.png": [DER], "spherical-support.png": [DER],
          "common-correspondences.png": [ORA, DER], "planar-vs-spherical-difference.png": [DER],
          "paired-reconstruction.png": [DER], "truth-error.png": [REF, DER], "conditioning.png": [DER]}
NOT_STATEMENT = ("An equivalence / control experiment: perfect correspondence, fixed head, favorable (safe-forward) gazes "
                 "only. Not a competition, not a near-baseline rescue, not a matcher, head-motion or controller run.")
SEL_NOTE = ("EXPERIMENT SELECTION: chosen by the predeclared rule (frozen NB1c RGB attention + calibration-only "
            "geometry); no depth, identity or stereo result; not a controller")
GAZE_COLORS = [S.OI_BLUE, S.OI_VERM, S.OI_GREEN]
PLANAR_C, SPHER_C = S.OI_ORANGE, S.OI_BLUE
ERR_RAMP, COND_RAMP, DIFF_RAMP = BV.ERR_RAMP, BV.COND_RAMP, BV.RANGE_RAMP
caption, stat_lines, region, header, frame, histogram, fmt_q = (BV.caption, BV.stat_lines, BV.region, BV.header, BV.frame,
                                                                 BV.histogram, BV.fmt_q)
png_bytes, gamma, ramp, colorbar, statement = BV.png_bytes, BV.gamma, BV.ramp, BV.colorbar, BV.statement

# the forward crop of the coarse sphere (NB1c grid, 0.5-degree cells)
CROP_YAW, CROP_PITCH, CELL_PX = (-42.0, 42.0), (-32.0, 32.0), 6


def sha256(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def npz(path: Path) -> dict:
    with np.load(path, allow_pickle=False) as z:
        return {k: np.asarray(z[k]) for k in z.files}


def j(path: Path):
    return json.loads(Path(path).read_text())


class Gaze:
    def __init__(self, run: Path, g: str, rec: dict):
        self.g, self.rec, self.rank = g, rec, rec["rank"]
        acq = run / "observations" / g / "acquisition"
        self.c = j(acq / "calibration.json")
        rgb = npz(acq / "rgb-observation.npz")
        self.rgb_L, self.rgb_R = rgb["rgb_L"], rgb["rgb_R"]
        self.prod = npz(run / "oracle" / g / "oracle-correspondences.npz")
        self.osum = j(run / "oracle" / g / "oracle-summary.json")
        self.rays = npz(run / "spherical" / g / "left-core-rays.npz")
        self.sph = npz(run / "spherical" / g / "epipolar-result.npz")
        self.ssum = j(run / "spherical" / g / "spherical-summary.json")
        self.pla = npz(run / "planar" / g / "planar-result.npz")
        self.psum = j(run / "planar" / g / "planar-summary.json")
        self.sup = j(run / "planar" / g / "planar-support.json")
        self.cmp = npz(run / "comparison" / g / "comparison-result.npz")
        self.evr = npz(run / "evaluation" / g / "evaluation-result.npz")
        self.files = [acq / "calibration.json", acq / "rgb-observation.npz",
                      run / "oracle" / g / "oracle-correspondences.npz", run / "oracle" / g / "oracle-summary.json",
                      run / "spherical" / g / "left-core-rays.npz", run / "spherical" / g / "epipolar-result.npz",
                      run / "spherical" / g / "spherical-summary.json", run / "planar" / g / "planar-result.npz",
                      run / "planar" / g / "planar-summary.json", run / "planar" / g / "planar-support.json",
                      run / "comparison" / g / "comparison-result.npz", run / "evaluation" / g / "evaluation-result.npz"]
        self.n = len(self.prod["left_core_row"])
        self.common = self.cmp["common"].astype(bool)
        self.vp, self.ve = self.pla["valid_planar"].astype(bool), self.sph["valid_epi"].astype(bool)
        n = SP.CORE_SIZE
        o = SP.CORE_ORIGIN
        self.core_rgb = self.rgb_L[o:o + n, o:o + n]
        self.mask = np.zeros((n, n), bool)
        self.mask[self.prod["left_core_row"], self.prod["left_core_col"]] = True
        self.cmask = np.zeros((n, n), bool)
        self.cmask[self.prod["left_core_row"][self.common], self.prod["left_core_col"][self.common]] = True

    def grid(self, values, sel=None) -> np.ndarray:
        n = SP.CORE_SIZE
        out = np.full((n, n), np.nan)
        m = np.ones(self.n, bool) if sel is None else sel
        out[self.prod["left_core_row"][m], self.prod["left_core_col"][m]] = np.asarray(values)[m]
        return out


class Data:
    def __init__(self, run: Path):
        self.run = run
        self.sel = j(run / "selection/selected-gazes.json")["gazes"]
        self.rounds = j(run / "selection/nms-rounds.json")["rounds"]
        self.ssum = j(run / "selection/selection-summary.json")
        self.mask = npz(run / "selection/safe-forward-mask.npz")
        self.A = npz(SP.ATTENTION[0])["A"]
        self.rgb_coarse = npz(SP.NB1C_RGB[0])["srgb8"]
        self.csum = j(run / "comparison/comparison-summary.json")
        self.ev = j(run / "evaluation/evaluation-summary.json")
        self.gz = [Gaze(run, g, rec) for g, rec in zip(SP.GAZES, self.sel)]
        self.sources = {str(SP.ATTENTION[0]): sha256(SP.ATTENTION[0]), str(SP.NB1C_RGB[0]): sha256(SP.NB1C_RGB[0])}
        for n in ("selection/selected-gazes.json", "selection/nms-rounds.json", "selection/selection-summary.json",
                  "selection/safe-forward-mask.npz", "comparison/comparison-summary.json",
                  "evaluation/evaluation-summary.json"):
            self.sources[n] = sha256(run / n)
        for z in self.gz:
            for p in z.files:
                self.sources[str(Path(p).relative_to(run))] = sha256(p)


# ------------------------------------------------------------------ helpers
def fmt_len(v: float | None) -> str:
    if v is None or not np.isfinite(v):
        return "—"
    a = abs(v)
    if a >= 0.1:
        return f"{v:.3f} m"
    if a >= 1e-4:
        return f"{v * 1e3:.3f} mm"
    if a >= 1e-7:
        return f"{v * 1e6:.3f} µm"
    return f"{v:.2e} m"


def qv(q: dict | None, key: str) -> float | None:
    return None if not q else q.get(key)


def label_selection(img, x, y) -> None:
    dr = ImageDraw.Draw(img)
    w = S.font(15, True).getlength(SP.SELECTION_LABEL) + 18
    S.dashed_rect(dr, [x, y, x + w, y + 26], S.INK, width=2, dash=6, gap=4)
    S.text(dr, (x + 9, y + 4), SP.SELECTION_LABEL, size=15, bold=True, outline=None)


def crop_px(yaw, pitch) -> tuple[float, float]:
    """Head yaw / pitch (deg) -> pixel in the forward crop (cell-centre convention)."""
    c0 = (CROP_YAW[0] + 180.0) / 0.5
    r0 = (90.0 - CROP_PITCH[1]) / 0.5
    return ((yaw + 180.0) / 0.5 - c0) * CELL_PX, ((90.0 - pitch) / 0.5 - r0) * CELL_PX


def crop_slices() -> tuple[slice, slice]:
    c0, c1 = int((CROP_YAW[0] + 180.0) / 0.5), int((CROP_YAW[1] + 180.0) / 0.5)
    r0, r1 = int((90.0 - CROP_PITCH[1]) / 0.5), int((90.0 - CROP_PITCH[0]) / 0.5)
    return slice(r0, r1), slice(c0, c1)


def yaw_pitch(d: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    d = np.asarray(d, np.float64)
    return np.degrees(np.arctan2(d[..., 0], -d[..., 2])), np.degrees(np.arctan2(d[..., 1], np.hypot(d[..., 0], d[..., 2])))


def ring(center_dir: np.ndarray, radius: float, n: int = 240) -> np.ndarray:
    z = FG.unit(center_dir)
    a = FG.unit(np.cross(z, [0.0, 1.0, 0.0]))
    b = np.cross(z, a)
    t = np.linspace(0, 2 * math.pi, n)
    return np.cos(radius) * z + np.sin(radius) * (np.cos(t)[:, None] * a + np.sin(t)[:, None] * b)


def sphere_panel(d: Data, kind: str) -> Image.Image:
    """The forward crop of the coarse sphere: RGB proxy or the frozen attention A, with the SAFE-FORWARD envelope."""
    rs, cs = crop_slices()
    if kind == "rgb":
        base = d.rgb_coarse[rs, cs].astype(np.float64)
    else:
        a = d.A[rs, cs]
        lo, hi = float(np.quantile(d.A, 0.01)), float(np.quantile(d.A, 0.999))
        base = ramp((a - lo) / (hi - lo), (np.array([250, 250, 245.]), np.array([90, 20, 70.]))).astype(np.float64)
    cone, elig = d.mask["cone"][rs, cs], d.mask["eligible"][rs, cs]
    dim = np.where(cone[..., None], 1.0, 0.45)
    out = (base * dim + (1 - dim) * 235).astype(np.uint8)
    img = Image.fromarray(out).resize((out.shape[1] * CELL_PX, out.shape[0] * CELL_PX), Image.NEAREST)
    # hatch outside the eligible set (outside the cone, and the cone cells failing the full-core leverage)
    m = Image.fromarray((~elig).astype(np.uint8) * 255).resize(img.size, Image.NEAREST)
    S.hatch(img, [0, 0, img.size[0], img.size[1]], (150, 146, 138), spacing=11, width=1, mask=m)
    dr = ImageDraw.Draw(img)
    cone_pts = [crop_px(*[float(v) for v in yp]) for yp in zip(*yaw_pitch(ring(np.array([0, 0, -1.0]),
                                                                              SP.FORWARD_CONE_RAD)))]
    S.dashed_line(dr, cone_pts + [cone_pts[0]], S.INK, width=3, dash=10, gap=6)
    fx, fy = crop_px(0.0, 0.0)
    dr.line([fx - 12, fy, fx + 12, fy], fill=S.INK, width=3)
    dr.line([fx, fy - 12, fx, fy + 12], fill=S.INK, width=3)
    S.text(dr, (fx + 10, fy + 12), "−Z forward", size=15, plate=S.WHITE)
    S.arrow(dr, img.size[0] - 150, 30, img.size[0] - 18, 30, color=S.INK2, width=3, head=14)
    S.text(dr, (img.size[0] - 152, 30), "+X baseline (yaw +90°)", size=15, plate=S.WHITE, anchor="rm")
    for k, g in enumerate(d.sel):
        dd = np.asarray(g["direction_h"])
        rp = [crop_px(*[float(v) for v in yp]) for yp in zip(*yaw_pitch(ring(dd, SP.D_MIN_RAD)))]
        S.dashed_line(dr, rp + [rp[0]], GAZE_COLORS[k], width=2, dash=7, gap=5)
    for k, g in enumerate(d.sel):
        x, y = crop_px(g["yaw_deg"], g["pitch_deg"])
        S.crosshair(dr, x, y, r=15, solid=True, color=GAZE_COLORS[k])
        S.text(dr, (x + 14, y - 30), str(g["rank"]), size=22, bold=True, fill=GAZE_COLORS[k], plate=S.WHITE)
    w, h = img.size
    for yaw in range(-40, 41, 20):
        x, _ = crop_px(float(yaw), 0.0)
        S.text(dr, (x, h - 4), f"{yaw:+d}°", size=13, fill=S.INK2, plate=S.WHITE, anchor="md")
    for pitch in range(-30, 31, 15):
        _, y = crop_px(0.0, float(pitch))
        S.text(dr, (4, y), f"{pitch:+d}°", size=13, fill=S.INK2, plate=S.WHITE, anchor="lm")
    dr.rectangle([0, 0, w - 1, h - 1], outline=S.INK2)
    return img


def raw_panel(z: Gaze, side: str, size: int, outline: bool = False) -> Image.Image:
    rgb = z.rgb_L if side == "L" else z.rgb_R
    img = Image.fromarray(gamma(rgb)).resize((size, size), Image.BILINEAR)
    dr = ImageDraw.Draw(img)
    s = size / SP.RAW_SIZE
    o, n = SP.CORE_ORIGIN, SP.CORE_SIZE
    S.dashed_rect(dr, [(o - 0.5) * s, (o - 0.5) * s, (o + n - 0.5) * s, (o + n - 0.5) * s], S.WHITE, width=3, dash=9,
                  gap=5)
    S.dashed_rect(dr, [(o - 0.5) * s + 2, (o - 0.5) * s + 2, (o + n - 0.5) * s - 2, (o + n - 0.5) * s - 2], S.INK,
                  width=1, dash=9, gap=5)
    if outline:
        poly = planar_outline(z, 0 if side == "L" else 1)
        dr.line([(float(u) * s, float(v) * s) for u, v in poly], fill=PLANAR_C, width=3)
    return img


def planar_outline(z: Gaze, side: int) -> np.ndarray:
    """The raw-raster boundary of the fixed central rectified core (accepted rectification maps)."""
    r = PL.rectify(z.c)
    x, y, cw, ch = map(int, r["crop_xywh"])
    s = "L" if side == 0 else "R"
    mx, my = r["map_" + s + "x"][y:y + ch, x:x + cw], r["map_" + s + "y"][y:y + ch, x:x + cw]
    edge = np.concatenate([np.stack([mx[0], my[0]], -1), np.stack([mx[:, -1], my[:, -1]], -1),
                           np.stack([mx[-1, ::-1], my[-1, ::-1]], -1), np.stack([mx[::-1, 0], my[::-1, 0]], -1)])
    return np.concatenate([edge, edge[:1]])


def core_layer(z: Gaze, values, sel, ends, log=False, lo=None, hi=None) -> tuple[np.ndarray, float, float]:
    g = z.grid(values, sel)
    m = np.isfinite(g)
    out = np.zeros(g.shape + (3,), np.uint8)
    out[:] = BV.NOCORR
    if not m.any():
        return out, 0.0, 0.0
    v = g[m]
    if log:
        v = np.log10(np.maximum(v, 1e-15))
    lo = float(np.quantile(v, 0.01)) if lo is None else lo
    hi = float(np.quantile(v, 0.99)) if hi is None else hi
    hi = hi if hi > lo else lo + 1e-12
    out[m] = ramp((v - lo) / (hi - lo), ends)
    return out, lo, hi


def paste_core(img, arr, x, y, size, nocorr_mask=None) -> None:
    img.paste(Image.fromarray(arr).resize((size, size), Image.NEAREST), (int(x), int(y)))
    if nocorr_mask is not None and nocorr_mask.any():
        m = Image.fromarray(nocorr_mask.astype(np.uint8) * 255).resize((size, size), Image.NEAREST)
        full = Image.new("L", img.size, 0)
        full.paste(m, (int(x), int(y)))
        S.hatch(img, [x, y, x + size, y + size], (196, 192, 184), spacing=10, width=1, mask=full)
    frame(ImageDraw.Draw(img), x, y, size, size)


def cloud(img, x, y, w, h, sets, title=None, vectors=None, view="top", origin=True) -> None:
    """Orthographic head-frame point clouds (top: X right / -Z up; side: -Z right / Y up)."""
    sub = Image.new("RGB", (int(w), int(h)), S.WHITE)
    dr = ImageDraw.Draw(sub)
    P = (lambda q: np.stack([q[..., 0], -q[..., 2]], -1)) if view == "top" else (lambda q: np.stack([-q[..., 2], q[..., 1]], -1))
    pts = [np.asarray(p, np.float64) for p, _ in sets if len(p)]
    allp = (np.concatenate(pts + ([np.zeros((1, 3))] if origin else [])) if pts else np.zeros((1, 3)))
    q = P(allp)
    lo, hi = q.min(0), q.max(0)
    span = float(max(hi - lo)) * 1.1 + 1e-6
    mid = (lo + hi) / 2
    pad = 30

    def to_px(v):
        v = (np.asarray(v) - mid) / span
        return pad + (v[..., 0] + 0.5) * (w - 2 * pad), h - pad - (v[..., 1] + 0.5) * (h - 2 * pad)
    step = 10 ** math.floor(math.log10(max(span / 4, 1e-3)))
    for k in range(-60, 61):
        for axis in (0, 1):
            a = np.array([k * step, lo[1] - span]) if axis == 0 else np.array([lo[0] - span, k * step])
            b = np.array([k * step, hi[1] + span]) if axis == 0 else np.array([hi[0] + span, k * step])
            (ax_, ay_), (bx_, by_) = to_px(a), to_px(b)
            dr.line([float(ax_), float(ay_), float(bx_), float(by_)], fill=S.GRID, width=1)
    arr = np.asarray(sub).copy()
    for p, col in sets:
        if not len(p):
            continue
        px, py = to_px(P(np.asarray(p)))
        xi, yi = np.clip(np.rint(px).astype(int), 0, int(w) - 2), np.clip(np.rint(py).astype(int), 0, int(h) - 2)
        c = np.asarray(col, np.uint8)
        arr[yi, xi] = c
        arr[yi + 1, xi] = c
    sub = Image.fromarray(arr)
    dr = ImageDraw.Draw(sub)
    if vectors is not None:
        base, vec, mag = vectors
        b0 = to_px(P(base))
        b1 = to_px(P(base + vec * mag))
        for k in range(len(base)):
            dr.line([float(b0[0][k]), float(b0[1][k]), float(b1[0][k]), float(b1[1][k])], fill=S.OI_VERM, width=2)
    if origin:
        o = to_px(P(np.zeros(3)))
        dr.ellipse([float(o[0]) - 4, float(o[1]) - 4, float(o[0]) + 4, float(o[1]) + 4], fill=S.INK)
    caption(dr, 6, 6, (title + "; " if title else "") + f"grid {step:g} m", size=13, fill=S.INK2)
    caption(dr, w / 2, h - 4, "head X (right)" if view == "top" else "head −Z (forward)", size=13, fill=S.INK2,
            anchor="md")
    dr.rectangle([0, 0, w - 1, h - 1], outline=S.INK2)
    img.paste(sub, (int(x), int(y)))


def gaze_tag(img, x, y, z: Gaze) -> None:
    dr = ImageDraw.Draw(img)
    S.crosshair(dr, x + 12, y + 13, r=10, solid=True, color=GAZE_COLORS[z.rank - 1])
    S.text(dr, (x + 30, y), f"gaze {z.rank}: ({z.rec['yaw_deg']:+.2f}°, {z.rec['pitch_deg']:+.2f}°)", size=18, bold=True,
           outline=None)


def gaze_numbers(z: Gaze) -> list[str]:
    r = z.rec
    return [f"α_forward {r['alpha_forward_deg']:.2f}°; L_center {r['L_center']:.4f}",
            f"min-core L {r['min_core_leverage_L']:.4f} / {r['min_core_leverage_R']:.4f}",
            f"B⊥ center {r['B_perp_center_m'] * 1000:.1f} mm; min-core {r['B_perp_min_core_m'] * 1000:.1f} mm",
            f"RGB attention A {r['A']:.4f}"]


# ------------------------------------------------------------------ figures
def safe_forward_selection(d: Data) -> Image.Image:
    rgb, att = sphere_panel(d, "rgb"), sphere_panel(d, "att")
    W = 40 + rgb.size[0] + 30 + att.size[0] + 40
    H = 200 + rgb.size[1] + 330
    img = Image.new("RGB", (W, H), S.SURFACE)
    header(img, "AB1c — SAFE-FORWARD gaze selection (frozen before any render)",
           [SEL_NOTE, "Left: the coarse spherical RGB (NB1c proxy, display).  Right: the frozen NB1c attention A.  "
                      "Forward crop yaw ±42°, pitch ±32°; unhatched = eligible."], [ORA, DER])
    label_selection(img, 40, 128)
    img.paste(rgb, (40, 170))
    img.paste(att, (40 + rgb.size[0] + 30, 170))
    dr = ImageDraw.Draw(img)
    caption(dr, 40, 170 + rgb.size[1] + 6, "coarse spherical RGB (ORACLE INPUT, display only)", size=15, fill=S.INK2)
    caption(dr, 40 + rgb.size[0] + 30, 170 + rgb.size[1] + 6, "frozen NB1c attention A (DERIVED; the only selection input)",
            size=15, fill=S.INK2)
    y0 = 170 + rgb.size[1] + 40
    s = d.ssum
    stat_lines(img, 40, y0, [
        "SAFE-FORWARD envelope (design eligibility, declared before any AB1c stereo result)",
        f"dashed: 20° forward cone about −Z ({s['cells_in_cone']:,} cells); hatched: outside the eligible set",
        f"full-core leverage min L ≥ 0.90 in both eyes removes {s['cone_cells_failing_leverage']:,} cone cells; "
        f"eligible {s['cells_eligible']:,}",
        f"K = 3; accepted NB1c tie rule and NMS inside the eligible set; dashed rings: D_MIN = {SP.D_MIN_DEG:.3f}°",
        f"boundary margins: |L_min − 0.90| ≥ {s['boundary_margins']['min_abs_leverage_minus_0p90']:.2e}; "
        f"|α − 20°| ≥ {s['boundary_margins']['min_abs_alpha_forward_minus_20deg_rad']:.2e} rad"],
        size=17, step=30, bold_first=True)
    x0 = 40 + rgb.size[0] + 30
    for k, g in enumerate(d.sel):
        z = d.gz[k]
        gaze_tag(img, x0, y0 + 4 + 96 * k, z)
        stat_lines(img, x0 + 30, y0 + 32 + 96 * k, [
            f"row {g['row']} col {g['col']}; A {g['A']:.4f}; α_fwd {g['alpha_forward_deg']:.2f}°; L_center {g['L_center']:.4f}",
            f"min-core L {g['min_core_leverage']:.4f}; eligible before {g['eligible_before']:,}; ties {g['tie_set_size']}; "
            f"suppressed {g['nms_suppressed']:,}"], size=15, step=24)
    return img


def binocular_observations(d: Data) -> Image.Image:
    s = 420
    W, H = 40 + 3 * (2 * s + 20) + 2 * 30 + 40 - 30, 230 + s + 210
    img = Image.new("RGB", (W, H), S.SURFACE)
    header(img, "AB1c — the three binocular observations (one physical observation per gaze)",
           ["Exactly one L / R pair was rendered at each frozen gaze (fixed head; accepted instrument; OPTIX 256 spp).  "
            "Both representations use these exact photons.", "Dashed square: the nominal 12° raw core (256 × 256 of "
                                                                "the 640 × 640 raster)."], [ORA])
    for k, z in enumerate(d.gz):
        x0 = 40 + k * (2 * s + 20 + 30)
        gaze_tag(img, x0, 150, z)
        for i, side in enumerate(("L", "R")):
            img.paste(raw_panel(z, side, s), (x0 + i * (s + 20), 190))
            frame(ImageDraw.Draw(img), x0 + i * (s + 20), 190, s, s)
            caption(ImageDraw.Draw(img), x0 + i * (s + 20), 190 + s + 4, f"raw {side}", size=14, fill=S.INK2)
        stat_lines(img, x0, 190 + s + 34, gaze_numbers(z), size=15, step=26)
    return img


def planar_support(d: Data) -> Image.Image:
    s = 400
    W, H = 40 + 3 * (2 * s + 20 + 30) - 30 + 40, 240 + s + 300
    img = Image.new("RGB", (W, H), S.SURFACE)
    header(img, "AB1c — planar support: the fixed central rectified core mapped back to the raw rasters",
           ["Accepted AB1a rectification (cv2.stereoRectify, CALIB_ZERO_DISPARITY, alpha −1).  Orange outline: raw source "
            "of the fixed central 256 × 256 rectified core;", "dashed: the intended nominal raw core.  Calibration only; "
                                                              "descriptive (no overlap threshold)."], [DER])
    for k, z in enumerate(d.gz):
        x0 = 40 + k * (2 * s + 20 + 30)
        gaze_tag(img, x0, 150, z)
        for i, side in enumerate(("L", "R")):
            img.paste(raw_panel(z, side, s, outline=True), (x0 + i * (s + 20), 190))
            frame(ImageDraw.Draw(img), x0 + i * (s + 20), 190, s, s)
        e = z.sup["eyes"]["L"]
        rr = z.psum["rectification"]
        stat_lines(img, x0, 190 + s + 14, [
            f"rectification rotation L / R {rr['R1_rotation_deg']:.3f}° / {rr['R2_rotation_deg']:.3f}°",
            f"rectified principal point L ({rr['principal_point_L_px'][0]:.1f}, {rr['principal_point_L_px'][1]:.1f}) px",
            f"rect. core from nominal raw core: {e['rectified_core_pixels_from_nominal_raw_core']:,} / 65,536 "
            f"({e['rectified_core_fraction_from_nominal_raw_core']:.3f})",
            f"raw source x {e['raw_source_of_rectified_core_px']['x'][0]:.1f}..{e['raw_source_of_rectified_core_px']['x'][1]:.1f}, "
            f"y {e['raw_source_of_rectified_core_px']['y'][0]:.1f}..{e['raw_source_of_rectified_core_px']['y'][1]:.1f}",
            f"core centre {e['rectified_core_centre_from_gaze_deg']:.3f}° from gaze, "
            f"{e['rectified_core_centre_from_baseline_deg']:.2f}° from baseline",
            f"finite {e['support_finite']}; two-dimensional {e['support_two_dimensional']}",
            "(AB1a gaze #1: 0 / 65,536; a 0.09 × 4.8 px sliver, 14.26° off)"], size=15, step=26)
    return img


def spherical_support(d: Data) -> Image.Image:
    s = 560
    W, H = 40 + 3 * (s + 40) + 40 - 40, 230 + s + 230
    img = Image.new("RGB", (W, H), S.SURFACE)
    header(img, "AB1c — spherical representation: every raw-core ray in the gaze-centered display chart",
           ["All 65,536 left raw-core rays (accepted AB1b rays / theta / phi), one dot each, RGB for display; "
            "chart_u = θ − θ_g, chart_v = sin θ_g · wrap(φ − φ_g).", "Display chart only, not a matcher raster.  "
                                                                     "Calibration only."], [DER])
    for k, z in enumerate(d.gz):
        x0 = 40 + k * (s + 40)
        gaze_tag(img, x0, 150, z)
        cu, cv = z.rays["chart_u"].ravel(), z.rays["chart_v"].ravel()
        lim = float(max(np.abs(cu).max(), np.abs(cv).max())) * 1.08
        sub = np.full((s, s, 3), 255, np.uint8)
        xi = np.clip(np.rint((cu / lim * 0.5 + 0.5) * (s - 1)).astype(int), 0, s - 1)
        yi = np.clip(np.rint((0.5 - cv / lim * 0.5) * (s - 1)).astype(int), 0, s - 1)
        sub[yi, xi] = gamma(z.core_rgb.reshape(-1, 3))
        img.paste(Image.fromarray(sub), (x0, 190))
        dr = ImageDraw.Draw(img)
        frame(dr, x0, 190, s, s)
        S.crosshair(dr, x0 + s / 2, 190 + s / 2, r=12, solid=True, color=GAZE_COLORS[k])
        lc = z.ssum["left_core"]
        stat_lines(img, x0, 190 + s + 12, [
            f"rays {lc['rays']:,}; finite {lc['finite']:,}; pole-singular {lc['pole_singular']}",
            f"θ {lc['theta_deg']['min']:.2f}..{lc['theta_deg']['max']:.2f}°; θ_g {z.ssum['theta_g_deg']:.2f}°",
            f"leverage sin θ {lc['leverage_sin_theta']['min']:.4f}..{lc['leverage_sin_theta']['max']:.4f}",
            f"chart extent ±{math.degrees(lim / 1.08):.2f}° (axes: chart_u right, chart_v up)"], size=15, step=26)
    return img


def common_correspondences(d: Data) -> Image.Image:
    s = 400
    W, H = 40 + 3 * (2 * s + 20 + 30) - 30 + 40, 240 + s + 260
    img = Image.new("RGB", (W, H), S.SURFACE)
    header(img, "AB1c — the ONE shared perfect-correspondence product per gaze (feeds BOTH geometries)",
           ["Left: left raw core; green = common valid pair (planar and spherical), hatched = no perfect correspondence.  "
            "Right: the matched right coordinates (continuous uv_R) in the padded right raster.",
            "Accepted AB1b oracle (Position / Object Index used only here); the product holds core row / col, uv_L, uv_R "
            "only."], [ORA, DER])
    for k, z in enumerate(d.gz):
        x0 = 40 + k * (2 * s + 20 + 30)
        gaze_tag(img, x0, 150, z)
        arr = (gamma(z.core_rgb).astype(np.float64) * 0.35 + 160).astype(np.uint8)
        arr[z.cmask] = np.array(S.OI_GREEN, np.uint8)
        only = z.mask & ~z.cmask
        arr[only] = np.array(S.OI_VERM, np.uint8)
        paste_core(img, arr, x0, 190, s, ~z.mask)
        sub = Image.fromarray(gamma(z.rgb_R)).resize((s, s), Image.BILINEAR)
        a = np.asarray(sub).astype(np.float64) * 0.35 + 160
        a = a.astype(np.uint8)
        uv = z.prod["uv_R"]
        if len(uv):
            xi = np.clip(np.rint(uv[:, 0] * s / SP.RAW_SIZE).astype(int), 0, s - 1)
            yi = np.clip(np.rint(uv[:, 1] * s / SP.RAW_SIZE).astype(int), 0, s - 1)
            a[yi, xi] = np.array(S.OI_GREEN, np.uint8)
        sub = Image.fromarray(a)
        dr = ImageDraw.Draw(sub)
        o, n, sc = SP.CORE_ORIGIN, SP.CORE_SIZE, s / SP.RAW_SIZE
        S.dashed_rect(dr, [(o - 0.5) * sc, (o - 0.5) * sc, (o + n - 0.5) * sc, (o + n - 0.5) * sc], S.INK, width=2)
        img.paste(sub, (x0 + s + 20, 190))
        frame(ImageDraw.Draw(img), x0 + s + 20, 190, s, s)
        k_ = d.csum["per_gaze"][z.g]["counts"]
        at = z.osum["attrition"]
        stat_lines(img, x0, 190 + s + 12, [
            f"perfect correspondences {z.osum['correspondences']:,} / 65,536 ({z.osum['fraction_of_core']:.3f})",
            "attrition " + " → ".join(f"{x['remaining']:,}" for x in at[1:]),
            f"no hit {z.osum['excluded']['no_finite_hit']:,}; instance 0 {z.osum['excluded']['hit_with_instance_0']:,}; "
            f"other right instance {z.osum['excluded']['different_right_instance']:,}",
            f"right matches outside the right nominal core {z.osum['right_margin']['outside_right_nominal_core']:,}",
            f"planar valid {k_['planar_valid']:,}; spherical valid {k_['spherical_valid']:,}; common {k_['common_valid']:,}",
            f"planar-only {k_['planar_only']:,}; spherical-only {k_['spherical_only']:,}"], size=15, step=26)
    return img


def magnification(dd: np.ndarray, span: float) -> float:
    p99 = float(np.quantile(dd, 0.99)) if dd.size else 0.0
    if p99 <= 0:
        return 1.0
    return float(10 ** round(math.log10(0.08 * span / p99)))


def difference(d: Data) -> Image.Image:
    s = 420
    W, H = 40 + 3 * (s + 30 + 520 + 40) - 40 + 40, 250 + s + 300
    img = Image.new("RGB", (W, H), S.SURFACE)
    header(img, "AB1c — direct planar vs spherical disagreement on the common valid set (PRIMARY; truth-free)",
           ["Left: ‖P_planar − P_spherical‖ over the left raw core (log10 m; hatched = no common pair).  Right: top view of "
            "the reconstruction with the difference vectors MAGNIFIED (factor stated).",
            "Both from the same frozen product and observation.  Control: the same pairs made exactly consistent "
            "(left-ray point at the spherical range)."], [DER])
    for k, z in enumerate(d.gz):
        x0 = 40 + k * (s + 30 + 520 + 40)
        gaze_tag(img, x0, 160, z)
        arr, lo, hi = core_layer(z, z.cmp["difference_m"], z.common, DIFF_RAMP, log=True)
        paste_core(img, arr, x0, 200, s, ~z.cmask)
        colorbar(img, x0 + 20, 200 + s + 40, s - 40, 14, lo, hi, ends=DIFF_RAMP, label="log10 ‖ΔP‖ [m]", fmt="{:.2f}")
        pts = z.sph["P_epi"][z.common]
        if len(pts):
            span = float(np.ptp(np.stack([pts[:, 0], -pts[:, 2]], -1), axis=0).max()) + 1e-6
            mag = magnification(z.cmp["difference_m"][z.common], span)
            idx = np.arange(0, len(pts), max(1, len(pts) // 160))
            vec = z.cmp["delta_planar_minus_spherical_m"][z.common][idx]
            cloud(img, x0 + s + 30, 200, 520, s, [(pts, (170, 175, 186))],
                  title=f"top view (eyes off-frame); red: ΔP × {mag:.0e}", vectors=(pts[idx], vec, mag), origin=False)
        else:
            statement(img, x0 + s + 30, 200, 520, s, ["no common pair", "nothing to compare"])
        c = d.csum["per_gaze"][z.g]
        dq, rq = c["planar_minus_spherical_m"], c["radial_signed_planar_minus_spherical_m"]
        cc = (c.get("consistency_restored_control") or {}).get("planar_minus_spherical_m")
        sk = c.get("oracle_skew", {})
        stat_lines(img, x0, 200 + s + 80, [
            f"common valid {c['counts']['common_valid']:,}",
            f"‖ΔP‖ median {fmt_len(qv(dq, 'median'))}, p95 {fmt_len(qv(dq, 'p95'))}, max {fmt_len(qv(dq, 'max'))}",
            f"signed radial median {fmt_len(qv(rq, 'median'))}, p95 {fmt_len(qv(rq, 'p95'))}",
            f"relative median {qv(c['relative_difference'], 'median') or 0:.2e}",
            f"oracle skew |φ res| median {qv(sk.get('abs_phi_residual_rad'), 'median') or 0:.2e} rad; "
            f"|row res| {qv(sk.get('abs_row_residual_px'), 'median') or 0:.2e} px",
            f"consistency-restored control: ‖ΔP‖ max {fmt_len(qv(cc, 'max'))}"], size=15, step=26)
    return img


def paired_reconstruction(d: Data) -> Image.Image:
    s = 520
    W, H = 40 + 3 * (s + 40) - 40 + 40, 240 + 2 * s + 30 + 160
    img = Image.new("RGB", (W, H), S.SURFACE)
    header(img, "AB1c — paired reconstructions: P_planar (orange) drawn over P_spherical (blue)",
           ["Common valid pairs; orthographic head-frame views (top: X right / −Z up; side: −Z right / Y up).  "
            "Where the planar dots hide the blue ones, the two agree at this scale.",
            "Truth-free (DERIVED).  The differences are micrometre-level: see the difference figure for magnified vectors."],
           [DER])
    for k, z in enumerate(d.gz):
        x0 = 40 + k * (s + 40)
        gaze_tag(img, x0, 150, z)
        ps, pp = z.sph["P_epi"][z.common], z.pla["P_planar"][z.common]
        for r, view in enumerate(("top", "side")):
            if len(ps):
                cloud(img, x0, 190 + r * (s + 30), s, s, [(ps, SPHER_C), (pp, PLANAR_C)], title=view, view=view)
            else:
                statement(img, x0, 190 + r * (s + 30), s, s, ["no common pair"])
        c = d.csum["per_gaze"][z.g]["counts"]
        stat_lines(img, x0, 190 + 2 * s + 40, [f"common {c['common_valid']:,} of {c['correspondences']:,} pairs",
                                                f"range (spherical) {fmt_q(z.ssum['distributions']['range_L_m'], 1, ' m', 3, ('min', 'median', 'max'))}"],
                   size=15, step=26)
    return img


def truth_error(d: Data) -> Image.Image:
    s = 620
    W, H = 40 + 3 * (s + 40) - 40 + 40, 240 + 2 * 300 + 300
    img = Image.new("RGB", (W, H), S.SURFACE)
    header(img, "AB1c — post-freeze REFERENCE / EVALUATION: both reconstructions against Position (secondary)",
           ["Position opened only after both geometries and the comparison were frozen.  3-D error histograms over each "
            "geometry's own valid pairs (log10 m).", "Descriptive; no pass / fail.  The truth error is bounded by the "
                                                     "Blender Position offset (AB1b supporting diagnostic) amplified by "
                                                     "the conditioning."], [REF, DER])
    for k, z in enumerate(d.gz):
        x0 = 40 + k * (s + 40)
        gaze_tag(img, x0, 150, z)
        ev = d.ev["per_gaze"][z.g]
        for r, (name, col, vk) in enumerate((("planar", PLANAR_C, z.vp), ("spherical", SPHER_C, z.ve))):
            e = z.evr[f"error_3d_{name}_m"][vk]
            e = np.log10(np.maximum(e[np.isfinite(e)], 1e-12))
            edges = np.linspace(-7, -2, 51)
            histogram(img, x0, 190 + r * 300, s, 270, e, edges, col, f"log10 3-D error [m] — {name}",
                      ticks=[(-7, "0.1 µm"), (-6, "1 µm"), (-5, "10 µm"), (-4, "0.1 mm"), (-3, "1 mm"), (-2, "1 cm")])
        stat_lines(img, x0, 190 + 600 + 10, [
            f"planar 3-D: median {fmt_len(qv(ev['planar_vs_truth']['error_3d_m'], 'median'))}, "
            f"p95 {fmt_len(qv(ev['planar_vs_truth']['error_3d_m'], 'p95'))}",
            f"spherical 3-D: median {fmt_len(qv(ev['spherical_vs_truth']['error_3d_m'], 'median'))}, "
            f"p95 {fmt_len(qv(ev['spherical_vs_truth']['error_3d_m'], 'p95'))}",
            f"signed radial (spherical) median {fmt_len(qv(ev['spherical_vs_truth']['radial_signed_m'], 'median'))}",
            f"reprojection L (planar / spherical) median "
            f"{qv(ev['planar_reprojection_px']['left'], 'median') or 0:.1e} / "
            f"{qv(ev['spherical_reprojection_px']['left'], 'median') or 0:.1e} px",
            f"composition: {ev['composition']['distinct_instances']} instances"], size=15, step=26)
    return img


def conditioning(d: Data) -> Image.Image:
    s = 620
    W, H = 40 + 3 * (s + 40) - 40 + 40, 240 + 3 * 250 + 220
    img = Image.new("RGB", (W, H), S.SURFACE)
    header(img, "AB1c — conditioning in the safe-forward regime (shown, not hidden)",
           ["κ = 1 / |sin γ| (γ = ray intersection angle), range per pixel-equivalent angle (spherical), planar disparity; "
            "common valid pairs.", "The favorable regime was chosen for strong transverse baseline; these are the "
                                   "resulting measured conditions, descriptive only."], [DER])
    for k, z in enumerate(d.gz):
        x0 = 40 + k * (s + 40)
        gaze_tag(img, x0, 150, z)
        m = z.common
        kap = z.sph["kappa"][m]
        rpp = z.sph["range_per_px"][m]
        disp = z.pla["disparity"][m]
        histogram(img, x0, 190, s, 230, kap, np.linspace(0, max(10.0, float(np.quantile(kap, 0.995)) if kap.size else 10), 51),
                  S.OI_GREEN, "κ = 1 / |sin γ|")
        histogram(img, x0, 190 + 250, s, 230, rpp,
                  np.linspace(0, max(1e-3, float(np.quantile(rpp, 0.995)) if rpp.size else 1e-3), 51), S.OI_SKY,
                  "range per pixel-equivalent angle [m]")
        histogram(img, x0, 190 + 500, s, 230, disp,
                  np.linspace(min(0.0, float(disp.min())) if disp.size else 0, max(1.0, float(np.quantile(disp, 0.995)))
                              if disp.size else 1, 51), PLANAR_C, "planar rectified disparity [px]")
        dd = z.ssum["distributions"]
        stat_lines(img, x0, 190 + 750 + 10, [
            f"κ median {qv(dd['kappa'], 'median') or 0:.1f}, p95 {qv(dd['kappa'], 'p95') or 0:.1f}",
            f"γ median {(qv(dd['ray_angle_gamma_rad'], 'median') or 0) * 1e3:.2f} mrad",
            f"range/px median {fmt_len(qv(dd['range_per_px_m'], 'median'))}",
            f"δθ > 0: {z.ssum['counts']['delta_theta_positive']:,} of {z.ssum['counts']['correspondences']:,}"],
            size=15, step=26)
    return img


def overview(d: Data) -> Image.Image:
    W, H = 2400, 2640
    img = Image.new("RGB", (W, H), S.SURFACE)
    header(img, "Active Bootstrap-1c — safe-forward planar vs spherical geometry",
           ["In the favorable regime, do planar and spherical geometry measure the same thing from the same photons?  "
            "Correspondence is held perfect: this compares REPRESENTATIONS only.", NOT_STATEMENT], [ORA, DER, REF])
    ax, aw = 40, W - 80
    # A
    ay, ah = 150, 640
    region(img, ax, ay, aw, ah, "A", "SAFE-FORWARD SELECTION (frozen before any render)", [ORA, DER])
    label_selection(img, ax + 20, ay + 56)
    att = sphere_panel(d, "att")
    sc = 520 / att.size[1]
    att = att.resize((int(att.size[0] * sc), 520), Image.LANCZOS)
    img.paste(att, (ax + 20, ay + 96))
    frame(ImageDraw.Draw(img), ax + 20, ay + 96, att.size[0], att.size[1])
    tx = ax + 20 + att.size[0] + 30
    stat_lines(img, tx, ay + 96, [
        "frozen NB1c RGB attention A, forward crop (yaw ±42°, pitch ±32°)",
        "dashed circle: 20° cone about −Z; hatched: not eligible",
        "eligible = cone ∧ min full-core leverage ≥ 0.90 (both eyes)",
        f"cone {d.ssum['cells_in_cone']:,} cells; eligible {d.ssum['cells_eligible']:,}",
        f"K = 3, accepted NB1c tie rule + NMS, D_MIN {SP.D_MIN_DEG:.2f}° (dashed rings)",
        "selection = RGB attention + calibration-only geometry;",
        "no depth / identity / stereo result selected the gazes"], size=17, step=31, bold_first=True)
    for k, z in enumerate(d.gz):
        gaze_tag(img, tx, ay + 330 + 92 * k, z)
        stat_lines(img, tx + 30, ay + 360 + 92 * k, [
            f"α_forward {z.rec['alpha_forward_deg']:.2f}°; min-core L {z.rec['min_core_leverage']:.4f}; "
            f"B⊥ ≥ {z.rec['B_perp_min_core_m'] * 1000:.1f} mm; A {z.rec['A']:.3f}"], size=16, step=26)
    # B
    by, bh = ay + ah + 20, 420
    region(img, ax, by, aw, bh, "B", "SAME PHYSICAL OBSERVATIONS (one binocular pair per gaze)", [ORA])
    s = 330
    for k, z in enumerate(d.gz):
        x0 = ax + 20 + k * (2 * s + 12 + 60)
        for i, side in enumerate(("L", "R")):
            img.paste(raw_panel(z, side, s), (x0 + i * (s + 12), by + 64))
            frame(ImageDraw.Draw(img), x0 + i * (s + 12), by + 64, s, s)
        S.text(ImageDraw.Draw(img), (x0, by + 64 + s + 6), f"gaze {z.rank}: raw L | raw R (dashed: nominal 12° core)",
               size=14, fill=S.INK2, outline=None)
    caption(ImageDraw.Draw(img), ax + 1200, by + 22, "both representations use these exact photons", size=17,
            bold=True)
    # C
    cy, ch = by + bh + 20, 580
    region(img, ax, cy, aw, ch, "C", "PLANAR vs SPHERICAL: same observation, SAME oracle matches", [ORA, DER])
    s = 300
    for k, z in enumerate(d.gz):
        x0 = ax + 20 + k * (2 * s + 20 + 106)
        gaze_tag(img, x0, cy + 56, z)
        img.paste(raw_panel(z, "L", s, outline=True), (x0, cy + 92))
        frame(ImageDraw.Draw(img), x0, cy + 92, s, s)
        arr = (gamma(z.core_rgb).astype(np.float64) * 0.35 + 160).astype(np.uint8)
        arr[z.cmask] = np.array(S.OI_GREEN, np.uint8)
        paste_core(img, arr, x0 + s + 20, cy + 92, s, ~z.mask)
        e = z.sup["eyes"]["L"]
        c = d.csum["per_gaze"][z.g]["counts"]
        stat_lines(img, x0, cy + 92 + s + 10, [
            "planar: orange = raw source of the rectified core",
            f"  from nominal core {e['rectified_core_fraction_from_nominal_raw_core']:.3f}; "
            f"centre {e['rectified_core_centre_from_gaze_deg']:.2f}° off gaze",
            "spherical: all 65,536 raw-core rays represented",
            f"shared product: {c['correspondences']:,} perfect pairs (green: common)",
            f"planar {c['planar_valid']:,} | spherical {c['spherical_valid']:,} | common {c['common_valid']:,}"],
            size=15, step=25)
    # D
    dy0 = cy + ch + 20
    dh = H - dy0 - 30
    region(img, ax, dy0, aw, dh, "D", "METRIC COMPARISON (direct: truth-free; truth: post-freeze)", [DER, REF])
    s = 300
    for k, z in enumerate(d.gz):
        x0 = ax + 20 + k * (2 * s + 20 + 106)
        gaze_tag(img, x0, dy0 + 56, z)
        pts = z.sph["P_epi"][z.common]
        if len(pts):
            cloud(img, x0, dy0 + 92, s, s, [(pts, SPHER_C), (z.pla["P_planar"][z.common], PLANAR_C)],
                  title="top; planar over spherical", origin=False)
        else:
            statement(img, x0, dy0 + 92, s, s, ["no common pair"])
        arr, lo, hi = core_layer(z, z.cmp["difference_m"], z.common, DIFF_RAMP, log=True)
        paste_core(img, arr, x0 + s + 20, dy0 + 92, s, ~z.cmask)
        caption(ImageDraw.Draw(img), x0 + s + 20, dy0 + 92 + s + 4,
                f"log10 ‖ΔP‖ {lo:.1f} (light) .. {hi:.1f} (dark) m", size=13, fill=S.INK2)
        c = d.csum["per_gaze"][z.g]
        ev = d.ev["per_gaze"][z.g]
        dq = c["planar_minus_spherical_m"]
        cc = (c.get("consistency_restored_control") or {}).get("planar_minus_spherical_m")
        stat_lines(img, x0, dy0 + 92 + s + 30, [
            f"‖P_planar − P_spherical‖ (DERIVED)",
            f"  median {fmt_len(qv(dq, 'median'))}; p95 {fmt_len(qv(dq, 'p95'))}; max {fmt_len(qv(dq, 'max'))}",
            f"  consistency-restored control max {fmt_len(qv(cc, 'max'))}",
            "vs Position (REFERENCE / EVALUATION), median / p95:",
            f"  planar {fmt_len(qv(ev['planar_vs_truth']['error_3d_m'], 'median'))} / "
            f"{fmt_len(qv(ev['planar_vs_truth']['error_3d_m'], 'p95'))}",
            f"  spherical {fmt_len(qv(ev['spherical_vs_truth']['error_3d_m'], 'median'))} / "
            f"{fmt_len(qv(ev['spherical_vs_truth']['error_3d_m'], 'p95'))}",
            f"κ median {qv(z.ssum['distributions']['kappa'], 'median') or 0:.1f}; range/px median "
            f"{fmt_len(qv(z.ssum['distributions']['range_per_px_m'], 'median'))}"], size=15, step=25)
    return img


def render_all(run: Path) -> tuple[dict, Data]:
    d = Data(run)
    figs = {"overview.png": overview(d), "safe-forward-selection.png": safe_forward_selection(d),
            "binocular-observations.png": binocular_observations(d), "planar-support.png": planar_support(d),
            "spherical-support.png": spherical_support(d), "common-correspondences.png": common_correspondences(d),
            "planar-vs-spherical-difference.png": difference(d), "paired-reconstruction.png": paired_reconstruction(d),
            "truth-error.png": truth_error(d), "conditioning.png": conditioning(d)}
    return figs, d


def visualize(run: Path, vis: Path) -> dict:
    vis.mkdir(parents=True, exist_ok=True)
    figs, d = render_all(run)
    out = {}
    for name in FIGURES:
        (vis / name).write_bytes(png_bytes(figs[name]))
        out[name] = {"sha256": sha256(vis / name), "badges": BADGES[name], "size": list(figs[name].size)}
    man = {"schema": "AB1c-visuals-manifest-v1", "figures": out, "sources": d.sources,
           "regenerate": ".venv/bin/python tools/active_bootstrap/ab1c_run.py visualize --run RUN --visuals VIS",
           "style": "Visual Language 1 (tools/visual_language/style.py)", "fonts": S.font_hashes(),
           "selection_label": SP.SELECTION_LABEL + ": caption label for the predeclared experiment selection; not a "
                                                   "Visual Language 1 class; nothing is CONTROLLER-TIME",
           "statement": NOT_STATEMENT}
    (vis / "visuals-manifest.json").write_text(json.dumps(man, indent=1, sort_keys=True) + "\n")
    print(f"[ab1c] visualize: {len(out)} figures -> {vis}")
    return man
