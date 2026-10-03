"""Natural Bootstrap-1c: the persistent human-facing figures.

Contract: docs/natural-bootstrap/nb1c-rgb-candidate-gaze-contract.md, section 17.  Reads the saved selection and
evaluation outputs, the RGB proxy, and (post-freeze, reference panels only) the frozen NB1a label raster and range
validity and the NB1b classes.  Draws with the accepted Visual Language 1 style and the accepted Breadth-1 / NB1b
panorama helpers, all read-only.  The RGB input, the attention field and the six gazes are the subject; range,
NB1a, NB1b and authored identity are the (secondary, muted) reference.
Glyphs:
- numbered ink crosshair (1-6): RGB gaze, in selection order (DERIVED, not executed);
- dashed ring, radius D_MIN: exclusion neighbourhood; solid ring, radius R_FULL: conservative full core;
- dotted ring R_CENTER and thin ring R_SURROUND: the receptive field (tangent-plane views);
- square outline: the nominal 12-degree core (tangent-plane views);
- hollow diamond P1, P2, S1-S3: accepted NB1b queued seeds (reference only); hatched: no range.
Deterministic: the checker regenerates every PNG byte-identically.
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
for p in (HERE, TOOLS / "classroom_oracle", TOOLS / "visual_language"):
    sys.path.insert(0, str(p))

import breadth1_visuals as B  # noqa: E402  (accepted Breadth-1 panorama helpers, read-only)
import nb1b_visuals as NB  # noqa: E402  (accepted NB1b sphere-ring, tangent-plane and class helpers, read-only)
import nb1c_run as R  # noqa: E402
import nb1c_spec as SP  # noqa: E402
import style as S  # noqa: E402  (Visual Language 1, read-only)

ORA, DER, REF = SP.TRUTH_ORACLE, SP.TRUTH_DERIVED, SP.TRUTH_REFERENCE
SC = 2
PW, PH = SP.WIDTH * SC, SP.HEIGHT * SC
SMALL = 16
FIGURES = ["overview.png", "rgb-input.png", "attention-map.png", "candidate-gazes.png", "center-surround-examples.png",
           "candidate-crops.png", "candidate-evaluation.png", "attention-score-distribution.png",
           "nb1b-reference-comparison.png"]
BADGES = {
    "overview.png": [ORA, DER, REF], "rgb-input.png": [ORA], "attention-map.png": [DER],
    "candidate-gazes.png": [DER, ORA], "center-surround-examples.png": [DER, ORA], "candidate-crops.png": [ORA, DER],
    "candidate-evaluation.png": [REF, DER], "attention-score-distribution.png": [DER],
    "nb1b-reference-comparison.png": [REF, DER],
}
HEAT = np.array([(253, 251, 242), (252, 222, 156), (244, 160, 74), (214, 92, 52), (150, 34, 72), (60, 12, 68)], np.float64)
GAZE_COLOR = S.INK
SEED_COLOR = S.REF_BROWN
GAZE_SHORT = {"GAZE_FULL_SAFE": "FULL-safe", "GAZE_CENTER_ONLY_SAFE": "CENTER-only-safe", "GAZE_UNSAFE": "unsafe",
              "GAZE_NO_RANGE": "no range"}
NB1B_CLASSES = ["ENVIRONMENT_CANDIDATE", "PRIMARY_LOOK", "SECONDARY_LOOK", "MARGINAL", "EDGE_ONLY"]
NB1B_SHORT = {"ENVIRONMENT_CANDIDATE": "environment", "PRIMARY_LOOK": "primary", "SECONDARY_LOOK": "secondary",
              "MARGINAL": "marginal", "EDGE_ONLY": "edge-only", None: "—"}


def sha256(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class Data:
    SOURCES = ["selection/attention-score.npz", "selection/attention-diagnostics.npz", "selection/candidate-gazes.json",
               "selection/nms-rounds.json", "selection/selection-summary.json", "evaluation/candidate-evaluation.json",
               "evaluation/nb1b-comparison.json"]
    EXTERNAL = {"rgb": SP.RGB_SOURCE,
                "labels": R.EVALUATION_INPUTS["nb1a/discovery/hypothesis-raster.npz"][0],
                "range": R.EVALUATION_INPUTS["nb1a/input/range-sensory.npz"][0],
                "serviceability": R.EVALUATION_INPUTS["nb1b/selection/serviceability.json"][0]}

    def __init__(self, run: Path):
        self.run = run
        j = lambda p: json.loads((run / p).read_text())  # noqa: E731
        self.gazes = j("selection/candidate-gazes.json")["gazes"]
        self.rounds = j("selection/nms-rounds.json")["rounds"]
        self.summ = j("selection/selection-summary.json")
        self.ev = j("evaluation/candidate-evaluation.json")
        self.nb = j("evaluation/nb1b-comparison.json")
        with np.load(run / "selection/attention-score.npz") as z:
            self.A = np.asarray(z["A"])
        with np.load(run / "selection/attention-diagnostics.npz") as z:
            self.diag = {k: np.asarray(z[k]) for k in z.files}
        with np.load(self.EXTERNAL["rgb"]) as z:
            self.srgb8 = np.asarray(z["srgb8"])
        with np.load(self.EXTERNAL["labels"]) as z:          # post-freeze, reference panels only
            self.labels = np.asarray(z["labels"], np.int64)
        with np.load(self.EXTERNAL["range"]) as z:
            self.valid = np.asarray(z["valid_mask"])
        recs = json.loads(self.EXTERNAL["serviceability"].read_text())["hypotheses"]
        lut = np.zeros(len(recs) + 1, np.int64)
        for r in recs:
            lut[r["label"]] = NB.SP.CLASSES.index(r["class"]) + 1
        self.cls = lut[self.labels]                          # 0 = no geometry, else 1 + NB1b class index
        self.dirs = SP.cell_directions_h().reshape(-1, 3)
        self.sources = {n: sha256(run / n) for n in self.SOURCES}
        self.sources.update({str(p): sha256(p) for p in self.EXTERNAL.values()})

    def d(self, g) -> np.ndarray:
        return self.dirs[g["row"] * SP.WIDTH + g["col"]]


# ------------------------------------------------------------------ colour and glyph helpers
def heat(t: np.ndarray) -> np.ndarray:
    t = np.clip(np.asarray(t, np.float64), 0, 1) * (len(HEAT) - 1)
    k = np.minimum(t.astype(np.int64), len(HEAT) - 2)
    f = (t - k)[..., None]
    return (HEAT[k] * (1 - f) + HEAT[k + 1] * f).round().astype(np.uint8)


def heat_scale(d: Data) -> float:
    """The colour limit: the 99.5th percentile of A (values above it saturate)."""
    return float(np.quantile(d.A, 0.995))


def heat_layer(d: Data, s: int = SC) -> np.ndarray:
    lim = heat_scale(d)
    return B.up(heat((d.A / lim) ** 0.7 if lim > 0 else np.zeros_like(d.A)), s)


def faded_rgb(d: Data, s: int = SC, keep: float = 0.45) -> np.ndarray:
    return B.up((keep * d.srgb8.astype(np.float64) + (1 - keep) * 255).round().astype(np.uint8), s)


def lin_to_srgb8(c) -> tuple:
    c = np.clip(np.asarray(c, np.float64), 0, 1)
    v = np.where(c <= 0.0031308, 12.92 * c, 1.055 * np.power(c, 1 / 2.4) - 0.055)
    return tuple(int(x) for x in np.round(v * 255))


def polyline_dash(dr, pts, fill, width=2, dash=9.0, gap=6.0) -> None:
    """Dashes along a polyline by arc length (the pattern continues across vertices)."""
    period, s0 = dash + gap, 0.0
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        L = math.hypot(x1 - x0, y1 - y0)
        if L == 0:
            continue
        t = 0.0
        while t < L:
            ph = (s0 + t) % period
            if ph < dash:
                e = min(L, t + dash - ph)
                dr.line([x0 + (x1 - x0) * t / L, y0 + (y1 - y0) * t / L, x0 + (x1 - x0) * e / L, y0 + (y1 - y0) * e / L],
                        fill=fill, width=width)
                t = e
            else:
                t = min(L, t + period - ph)
        s0 += L


def wrap(lines: list[str], width_px: int, size: int = S.T_SMALL) -> list[str]:
    """Greedy word wrap of header lines to a pixel width (DejaVu metrics)."""
    f = S.font(size)
    out = []
    for ln in lines:
        cur = ""
        for word in ln.split(" "):
            cand = word if not cur else cur + " " + word
            if f.getlength(cand) <= width_px or not cur:
                cur = cand
            else:
                out.append(cur)
                cur = "  " + word
        out.append(cur)
    return out


def pano(content, title, lines, badges, after=None, legend=None) -> Image.Image:
    return B.pano_figure(content, title, wrap(lines, PW + 30), badges, legend=legend, after=after)


def sphere_ring(dr, d_s, radius, ox, oy, w=PW, h=PH, style="solid", color=S.INK, width=2) -> None:
    """A spherical circle projected to the panorama, split at the longitude seam."""
    yaw, pitch = NB.circle_yaw_pitch(d_s, radius, n=360)
    pts = [(ox + (y + 180) / 360 * w, oy + (90 - p) / 180 * h) for y, p in zip(yaw.tolist(), pitch.tolist())]
    runs, cur = [], [pts[0]]
    for a, b in zip(pts[:-1], pts[1:]):
        if abs(b[0] - a[0]) > w / 2:
            runs.append(cur)
            cur = [b]
        else:
            cur.append(b)
    runs.append(cur)
    for run in runs:
        if len(run) < 2:
            continue
        if style == "solid":
            dr.line(run, fill=S.WHITE, width=width + 3)
            dr.line(run, fill=color, width=width)
        else:
            dash, gap = (10.0, 7.0) if style == "dashed" else (3.0, 4.0)
            polyline_dash(dr, run, S.WHITE, width=width + 3, dash=dash, gap=gap)
            polyline_dash(dr, run, color, width=width, dash=dash, gap=gap)


def gaze_glyph(dr, g: dict, ox: int, oy: int, w: int = PW, h: int = PH, r: int = 11, label: bool = True,
               size: int = SMALL) -> None:
    x, y = B.xy(g["yaw_deg"], g["pitch_deg"], w, h)
    S.crosshair(dr, ox + x, oy + y, r=r, color=GAZE_COLOR, width=2)
    if label:
        S.text(dr, (ox + x + 2.2 * r, oy + y - 1.6 * r), str(g["rank"]), size=size + 2, bold=True, plate=S.WHITE,
               anchor="mm")


def seed_glyph(dr, e: dict, ox: int, oy: int, w: int = PW, h: int = PH, label: bool = True) -> None:
    x, y = B.xy(e["yaw_deg"], e["pitch_deg"], w, h)
    pts = [(ox + x, oy + y - 7), (ox + x + 7, oy + y), (ox + x, oy + y + 7), (ox + x - 7, oy + y), (ox + x, oy + y - 7)]
    dr.line(pts, fill=S.WHITE, width=5)
    dr.line(pts, fill=SEED_COLOR, width=2)
    if label:
        S.text(dr, (ox + x - 12, oy + y + 14), e["seed"], size=SMALL - 2, bold=True, fill=SEED_COLOR, plate=S.WHITE,
               anchor="mm")


def gaze_rings(dr, d: Data, ox: int, oy: int, w: int = PW, h: int = PH, exclusion: bool = True, full: bool = True) -> None:
    for g in d.gazes:
        if exclusion:
            sphere_ring(dr, d.d(g), SP.D_MIN_RAD, ox, oy, w, h, style="dashed", width=2)
        if full:
            sphere_ring(dr, d.d(g), SP.R_FULL_RAD, ox, oy, w, h, style="solid", width=2)


def legend(img, dr, x, y, items) -> None:
    for kind, label in items:
        if kind == "gaze":
            S.crosshair(dr, x + 13, y + 11, r=7, color=GAZE_COLOR, width=2)
        elif kind == "dmin":
            S.dashed_ellipse(dr, [x + 2, y, x + 24, y + 22], S.INK, width=2, n=10)
        elif kind == "full":
            dr.ellipse([x + 2, y, x + 24, y + 22], outline=S.INK, width=2)
        elif kind == "center":
            S.dashed_ellipse(dr, [x + 6, y + 4, x + 20, y + 18], S.INK, width=2, n=8)
        elif kind == "surround":
            dr.ellipse([x, y - 2, x + 26, y + 24], outline=S.INK2, width=1)
        elif kind == "square":
            dr.rectangle([x + 3, y + 1, x + 23, y + 21], outline=S.INK, width=2)
        elif kind == "seed":
            pts = [(x + 13, y + 3), (x + 21, y + 11), (x + 13, y + 19), (x + 5, y + 11), (x + 13, y + 3)]
            dr.line(pts, fill=SEED_COLOR, width=2)
        elif kind == "nogeom":
            dr.rectangle([x, y + 1, x + 26, y + 21], fill=B.NO_GEOM, outline=S.MUTED)
            S.hatch(img, [x, y + 1, x + 26, y + 21], S.STIPPLE, spacing=6, width=1)
            dr = ImageDraw.Draw(img)
        elif kind in NB.CLASS_STYLE:
            dr.rectangle([x, y + 1, x + 26, y + 21], fill=muted_class_color(kind), outline=S.INK2)
        bb = S.text(dr, (x + 36, y + 11), label, size=SMALL, outline=None, anchor="lm")
        x = bb[2] + 28


def muted_class_color(c: str, keep: float = 0.45) -> tuple:
    col = np.array(NB.ENV_FILL if c == NB.SP.ENVIRONMENT else NB.CLASS_STYLE[c]["color"], np.float64)
    return tuple(int(v) for v in (keep * col + (1 - keep) * 255).round())


def class_layer(d: Data, s: int = SC) -> np.ndarray:
    """REFERENCE: every NB1a hypothesis filled (muted) by its frozen NB1b class; no geometry left pale."""
    col = np.full(d.labels.shape + (3,), 255, np.uint8)
    for k, c in enumerate(NB.SP.CLASSES, start=1):
        col[d.cls == k] = muted_class_color(c)
    col[~d.valid] = B.NO_GEOM
    img = B.up(col, s)
    img[B.boundary_mask(d.labels, s)] = (175, 175, 175)
    return img


def colorbar(img: Image.Image, x: int, y: int, w: int, h: int, lim: float) -> None:
    t = np.linspace(0, 1, w)
    bar = heat(t ** 0.7)[None].repeat(h, axis=0)
    img.paste(Image.fromarray(bar), (x, y))
    dr = ImageDraw.Draw(img)
    dr.rectangle([x - 1, y - 1, x + w, y + h], outline=S.INK2)
    for f in (0.0, 0.5, 1.0):
        dr.line([x + f * w, y + h, x + f * w, y + h + 4], fill=S.INK2)
        S.text(dr, (x + f * w, y + h + 6), f"{f * lim:.3g}" + (" = p99.5 of A (above saturates)" if f == 1.0 else ""),
               size=SMALL - 3, fill=S.INK2, outline=None, anchor="ma" if f < 1 else "ra")


# ------------------------------------------------------------------ tangent-plane views
def tangent_rgb(d: Data, d_s, npx: int, half_deg: float) -> Image.Image:
    cells = NB.gnomonic_cells(d_s, npx, half_deg)
    return Image.fromarray(d.srgb8.reshape(-1, 3)[cells].copy())


def tangent_circle(dr, ox, oy, npx, half_deg, radius, style="solid", color=S.INK, width=2) -> None:
    k = npx / (2 * math.tan(math.radians(half_deg)))
    r = math.tan(radius) * k
    cx, cy = ox + npx / 2, oy + npx / 2
    box = [cx - r, cy - r, cx + r, cy + r]
    if style == "solid":
        dr.ellipse(box, outline=S.WHITE, width=width + 3)
        dr.ellipse(box, outline=color, width=width)
    else:
        S.dashed_ellipse(dr, box, S.WHITE, width=width + 3, n=28 if style == "dotted" else 16)
        S.dashed_ellipse(dr, box, color, width=width, n=28 if style == "dotted" else 16)


def tangent_square(dr, ox, oy, npx, half_deg, color=S.INK) -> None:
    k = npx / (2 * math.tan(math.radians(half_deg)))
    a = math.tan(SP.R_CENTER_RAD) * k
    cx, cy = ox + npx / 2, oy + npx / 2
    dr.rectangle([cx - a, cy - a, cx + a, cy + a], outline=S.WHITE, width=5)
    dr.rectangle([cx - a, cy - a, cx + a, cy + a], outline=color, width=2)


def support_tile(d: Data, g: dict, e: dict, npx: int, half_deg: float) -> Image.Image:
    """REFERENCE: the gaze cell's NB1a hypothesis (its NB1b class colour), other hypotheses (light), no range."""
    cells = NB.gnomonic_cells(d.d(g), npx, half_deg)
    lab = d.labels.reshape(-1)[cells]
    img = np.full((npx, npx, 3), 236, np.uint8)
    own = e["nb1a_label"] or -1
    if e["nb1b_class"]:
        c = e["nb1b_class"]
        img[lab == own] = NB.ENV_FILL if c == NB.SP.ENVIRONMENT else NB.CLASS_STYLE[c]["color"]
    img[lab == 0] = B.NO_GEOM
    edge = np.zeros(lab.shape, bool)
    edge[:, 1:] |= lab[:, 1:] != lab[:, :-1]
    edge[1:, :] |= lab[1:, :] != lab[:-1, :]
    img[edge] = S.INK2
    out = Image.fromarray(img)
    S.hatch(out, [0, 0, npx, npx], S.STIPPLE, spacing=7, width=1, mask=Image.fromarray(((lab == 0) * 255).astype(np.uint8)))
    return out


# ------------------------------------------------------------------ figures
def rgb_input(d: Data) -> Image.Image:
    return pano(B.up(d.srgb8, SC), "ORACLE INPUT · the coarse spherical RGB proxy",
                         ["the only scene data selection reads; " f"rgb-sensory.npz: 720 × 360 cells (0.5°), 8-bit sRGB of the accepted Breadth-1 render "
                          f"(sha256 {SP.RGB_SHA256[:12]}…); a controlled sensory proxy from Blender",
                          "selection converts it to linear RGB (standard sRGB transfer) and reads nothing else: no "
                          "depth, no validity mask, no hypotheses, no identity"],
                         BADGES["rgb-input.png"])


def attention_map(d: Data) -> Image.Image:
    lim = heat_scale(d)
    s = d.summ["attention_score"]

    def after(img, dr, L, T):
        for g in d.gazes:
            gaze_glyph(dr, g, L, T)

    return pano(heat_layer(d), "DERIVED · the center-surround attention field A(g)",
                         [f"every one of the {d.summ['candidate_directions']:,} cell centres is a candidate; CENTER = 6° "
                          f"disk, SURROUND = 6–12° annulus, solid-angle weighted linear RGB",
                          f"A: min {s['min']:.3g}, median {s['median']:.3g}, p90 {s['p90']:.3g}, p95 {s['p95']:.3g}, "
                          f"p99 {s['p99']:.3g}, max {s['max']:.3g}; colour ∝ (A / p99.5)^0.7; crosshairs: the six "
                          "selected gazes"],
                         BADGES["attention-map.png"], after=after,
                         legend=lambda img, dr, x, y: (legend(img, dr, x, y, [("gaze", "selected gaze (order 1–6)")]),
                                                       colorbar(img, x + 560, y + 4, 600, 18, lim)))


def candidate_gazes(d: Data) -> Image.Image:
    def after(img, dr, L, T):
        gaze_rings(dr, d, L, T)
        for g in d.gazes:
            gaze_glyph(dr, g, L, T)

    pw = d.summ["min_pairwise_deg"]
    return pano(faded_rgb(d), "DERIVED · six RGB candidate gazes (not executed)",
                         ["greedy spherical NMS on A: take the eligible maximum (ties: smaller row, then column), suppress "
                          f"every candidate closer than D_MIN = 2·R_FULL = {SP.D_MIN_DEG:.3f}°, repeat until six",
                          f"dashed: D_MIN exclusion neighbourhood; solid: R_FULL = {SP.R_FULL_DEG:.3f}° full-core "
                          f"neighbourhood (disjoint between gazes); minimum pairwise separation {pw:.3f}°",
                          "K = 6 is an attention budget, not an object count; no score threshold; gazes never moved"],
                         BADGES["candidate-gazes.png"], after=after,
                         legend=lambda img, dr, x, y: legend(img, dr, x, y, [("gaze", "RGB gaze 1–6"),
                                                                             ("dmin", f"D_MIN {SP.D_MIN_DEG:.2f}°"),
                                                                             ("full", f"R_FULL {SP.R_FULL_DEG:.2f}°")]))


def stat_lines(g: dict) -> list[str]:
    return [f"A = {g['A']:.4g}", f"D_RGB = {g['D_RGB']:.4g}", f"V_C = {g['V_C']:.3g}", f"V_S = {g['V_S']:.3g}",
            f"cells C / S = {g['n_C']} / {g['n_S']}"]


def center_surround_examples(d: Data) -> Image.Image:
    npx, half = 340, 14.0
    cols = 3
    img = Image.new("RGB", (110 + cols * (npx + 400), 230 + 2 * (npx + 140)), S.SURFACE)
    B.header(img, "DERIVED · the receptive field at each selected gaze: 6° center vs 6–12° surround",
             ["tangent-plane RGB view ±14° around each gaze; dotted: CENTER 6° (R_CENTER = CORE_FOV/2); thin solid: "
              "SURROUND edge 12° (R_SURROUND = CORE_FOV); swatches: weighted means μ_C, μ_S (shown in sRGB)",
              "A rewards a center that differs from its surround (D_RGB) and is internally coherent (small V_C + V_S); "
              "not objectness, not saliency ground truth"], BADGES["center-surround-examples.png"])
    for k, g in enumerate(d.gazes):
        x = 110 + (k % cols) * (npx + 400)
        y = 200 + (k // cols) * (npx + 140)
        img.paste(tangent_rgb(d, d.d(g), npx, half), (x, y))
        dr = ImageDraw.Draw(img)
        tangent_circle(dr, x, y, npx, half, SP.R_CENTER_RAD, style="dotted")
        tangent_circle(dr, x, y, npx, half, SP.R_SURROUND_RAD, style="solid", width=1)
        dr.rectangle([x - 1, y - 1, x + npx, y + npx], outline=S.INK2)
        S.text(dr, (x + 8, y + 8), str(g["rank"]), size=S.T_HEAD, bold=True, plate=S.WHITE)
        tx = x + npx + 24
        S.text(dr, (tx, y), f"gaze {g['rank']} · yaw {g['yaw_deg']:+.2f}°, pitch {g['pitch_deg']:+.2f}°", size=SMALL,
               bold=True, outline=None)
        for j, (lab, mu) in enumerate((("μ_C", g["mu_C_linear"]), ("μ_S", g["mu_S_linear"]))):
            yy = y + 36 + 46 * j
            dr.rectangle([tx, yy, tx + 60, yy + 36], fill=lin_to_srgb8(mu), outline=S.INK2)
            S.text(dr, (tx + 72, yy + 18), f"{lab} = ({mu[0]:.3f}, {mu[1]:.3f}, {mu[2]:.3f})", size=SMALL - 2,
                   outline=None, anchor="lm")
        for j, ln in enumerate(stat_lines(g)):
            S.text(dr, (tx, y + 136 + 28 * j), ln, size=SMALL - 1, outline=None, bold=(j == 0))
    dr = ImageDraw.Draw(img)
    legend(img, dr, 110, img.size[1] - 46, [("center", "CENTER 6°"), ("surround", "SURROUND edge 12°")])
    return img


def candidate_crops(d: Data) -> Image.Image:
    npx, half = 300, 20.0
    img = Image.new("RGB", (110 + 6 * (npx + 30), 230 + npx + 120), S.SURFACE)
    B.header(img, "ORACLE INPUT · RGB appearance around each RGB gaze (human inspection)",
             ["tangent-plane view ±20°; square: the nominal 12° measurement core; solid ring: R_FULL (circumscribing the "
              "core); dotted: CENTER 6°", "the gazes are proposals only: no foveation, no stereo, nothing executed"],
             BADGES["candidate-crops.png"])
    for k, g in enumerate(d.gazes):
        x, y = 110 + k * (npx + 30), 200
        img.paste(tangent_rgb(d, d.d(g), npx, half), (x, y))
        dr = ImageDraw.Draw(img)
        tangent_square(dr, x, y, npx, half)
        tangent_circle(dr, x, y, npx, half, SP.R_FULL_RAD)
        tangent_circle(dr, x, y, npx, half, SP.R_CENTER_RAD, style="dotted")
        dr.rectangle([x - 1, y - 1, x + npx, y + npx], outline=S.INK2)
        S.text(dr, (x + 8, y + 8), str(g["rank"]), size=S.T_HEAD, bold=True, plate=S.WHITE)
        S.text(dr, (x, y + npx + 10), f"gaze {g['rank']}: yaw {g['yaw_deg']:+.2f}°, pitch {g['pitch_deg']:+.2f}°",
               size=SMALL - 2, bold=True, outline=None)
        S.text(dr, (x, y + npx + 34), f"A {g['A']:.4g} · D_RGB {g['D_RGB']:.3g}", size=SMALL - 3, fill=S.INK2,
               outline=None)
    return img


def eval_lines(e: dict) -> list[str]:
    rng = f"{e['range_m']:.3f} m" if e["range_m"] is not None else "no valid range"
    ref = e["reference_at_gaze"]
    refs = ref["kind"] if ref["kind"] != "authored" else f"authored {ref['name']}"
    out = [f"{e['nb1a_hypothesis'] or 'no hypothesis'} · NB1b {NB1B_SHORT[e['nb1b_class']]}",
           f"range {rng}", f"at the gaze: {GAZE_SHORT[e['gaze_class']]}"]
    if e["valid_range"]:
        out.append(f"CENTER {e['center']['own_cells']}/{e['center']['total_cells']} · FULL "
                   f"{e['full']['own_cells']}/{e['full']['total_cells']}")
    out.append(f"reference: {refs}"[:44])
    return out


def candidate_evaluation(d: Data) -> Image.Image:
    npx, half = 300, 12.0
    img = Image.new("RGB", (110 + 6 * (npx + 30), 230 + npx + 420), S.SURFACE)
    agg = d.ev["aggregate"]
    B.header(img, "REFERENCE / EVALUATION (post-freeze) · the six RGB gazes against range, NB1a, NB1b",
             ["tangent plane ±12° at each RGB gaze itself (not at an NB1a seed): its NB1a hypothesis in the NB1b class "
              "colour, other hypotheses light, no range hatched; dotted CENTER 6°, solid FULL "
              f"{SP.R_FULL_DEG:.2f}°, square: the 12° core",
              "descriptive only: computed after the RGB freeze; changes no gaze and no order; no target; not ground truth"],
             BADGES["candidate-evaluation.png"])
    for k, (g, e) in enumerate(zip(d.gazes, d.ev["gazes"])):
        x, y = 110 + k * (npx + 30), 200
        img.paste(support_tile(d, g, e, npx, half), (x, y))
        dr = ImageDraw.Draw(img)
        tangent_square(dr, x, y, npx, half)
        tangent_circle(dr, x, y, npx, half, SP.R_FULL_RAD)
        tangent_circle(dr, x, y, npx, half, SP.R_CENTER_RAD, style="dotted")
        S.crosshair(dr, x + npx / 2, y + npx / 2, r=7, color=GAZE_COLOR, width=2)
        dr.rectangle([x - 1, y - 1, x + npx, y + npx], outline=S.INK2)
        S.text(dr, (x + 8, y + 8), str(g["rank"]), size=S.T_HEAD, bold=True, plate=S.WHITE)
        for j, ln in enumerate(eval_lines(e)):
            S.text(dr, (x, y + npx + 10 + 26 * j), ln, size=SMALL - 3, bold=(j == 0), outline=None)
    dr = ImageDraw.Draw(img)
    y0 = 200 + npx + 170
    S.text(dr, (110, y0), "Across the six (counts; no target declared)", size=S.T_SMALL, bold=True, outline=None)
    groups = [[("valid range", agg["valid_range"]), ("no valid range", agg["no_valid_range"]),
               ("distinct NB1a hypotheses", agg["distinct_nb1a_hypotheses"]),
               ("duplicate gazes into one hypothesis", agg["duplicate_gazes_into_same_hypothesis"])],
              [(f"lands on NB1b {NB1B_SHORT[c]}", agg["nb1b_class_hits"][c]) for c in NB1B_CLASSES],
              [(f"at the gaze: {GAZE_SHORT[c]}", agg["gaze_class_counts"][c]) for c in R.GAZE_CLASSES]]
    for gi, rows in enumerate(groups):
        for j, (lab, n) in enumerate(rows):
            cx, cy = 110 + gi * 640, y0 + 40 + 34 * j
            if n:
                dr.rectangle([cx + 400, cy + 2, cx + 400 + 30 * n, cy + 22], fill=(200, 200, 196), outline=S.INK2)
            S.text(dr, (cx, cy + 12), lab, size=SMALL - 1, outline=None, anchor="lm")
            S.text(dr, (cx + 380, cy + 12), str(n), size=SMALL - 1, bold=True, outline=None, anchor="rm")
    legend(img, dr, 110, img.size[1] - 46, [(c, NB1B_SHORT[c]) for c in NB.SP.CLASSES] + [("nogeom", "no range")])
    return img


def attention_score_distribution(d: Data) -> Image.Image:
    img = Image.new("RGB", (2100, 1060), S.SURFACE)
    s = d.summ["attention_score"]
    B.header(img, "DERIVED · attention-score distribution over all candidates, and the six NMS rounds",
             [f"left: histogram of A over the {d.summ['candidate_directions']:,} candidates (log counts, log A bins; "
              "exact zeros counted separately); markers: percentiles and the six selected scores",
              "right: greedy NMS rounds (no score threshold: even a poor sixth proposal is kept, K is a budget)"],
             BADGES["attention-score-distribution.png"])
    dr = ImageDraw.Draw(img)
    a = d.A.reshape(-1)
    pos = a[a > 0]
    zeros = int((a <= 0).sum())
    lo = math.log10(max(float(pos.min()), 1e-12)) if pos.size else -3.0
    hi = math.log10(float(pos.max())) if pos.size else 0.0
    lo = math.floor(lo * 2) / 2
    hi = math.ceil(hi * 2) / 2 + 1e-9
    x0, y0, pw, ph = 140, 220, 1100, 620
    nb = 60
    edges = np.linspace(lo, hi, nb + 1)
    cnt, _ = np.histogram(np.log10(pos), bins=edges)
    top = math.log10(max(1, int(cnt.max())) + 1)
    for k, c in enumerate(cnt.tolist()):
        if c:
            hgt = math.log10(c + 1) / top * ph
            bx = x0 + k / nb * pw
            dr.rectangle([bx, y0 + ph - hgt, bx + pw / nb - 1, y0 + ph], fill=(214, 92, 52), outline=None)
    dr.rectangle([x0, y0, x0 + pw, y0 + ph], outline=S.INK2)

    def px(v):
        return x0 + (math.log10(v) - lo) / (hi - lo) * pw
    for e in range(math.ceil(lo), math.floor(hi) + 1):
        S.text(dr, (px(10.0 ** e), y0 + ph + 8), f"1e{e}", size=SMALL - 2, fill=S.INK2, outline=None, anchor="ma")
    for j, name in enumerate(("median", "p90", "p95", "p99")):
        if s[name] > 0:
            x = px(s[name])
            S.dashed_line(dr, [(x, y0 - 6 - 20 * (j % 2)), (x, y0 + ph)], S.INK2, width=1, dash=5, gap=4)
            S.text(dr, (x, y0 - 10 - 20 * (j % 2)), f"{name} {s[name]:.3g}", size=SMALL - 4, fill=S.INK2, outline=None,
                   anchor="md")
    for g in d.gazes:
        if g["A"] > 0:
            x = px(g["A"])
            dr.line([x, y0 + ph - 40, x, y0 + ph], fill=S.INK, width=2)
            S.text(dr, (x, y0 + ph - 46 - 18 * ((g["rank"] - 1) % 3)), str(g["rank"]), size=SMALL - 2, bold=True,
                   plate=S.WHITE, anchor="md")
    S.text(dr, (x0 + pw / 2, y0 + ph + 40), "A (log scale)", size=SMALL, fill=S.INK2, outline=None, anchor="ma")
    S.text(dr, (x0, y0 + ph + 74), f"exact zeros (not drawn): {zeros:,}; min {s['min']:.3g}, max {s['max']:.4g}",
           size=SMALL - 1, outline=None)
    tx, ty = 1320, 230
    hdr = ["round", "score A", "tie set", "eligible before", "suppressed", "remaining", "margin"]
    xs = [tx, tx + 80, tx + 220, tx + 310, tx + 470, tx + 590, tx + 700]
    for x, hcell in zip(xs, hdr):
        S.text(dr, (x, ty), hcell, size=SMALL - 3, bold=True, outline=None)
    for k, r in enumerate(d.rounds):
        yy = ty + 40 + 34 * k
        vals = [str(r["round"]), f"{r['score']:.4g}", str(r["tie_set_size"]), f"{r['eligible_before']:,}",
                f"{r['newly_suppressed']:,}", f"{r['remaining']:,}",
                "—" if r["margin_to_next_eligible"] is None else f"{r['margin_to_next_eligible']:.3g}"]
        for x, v in zip(xs, vals):
            S.text(dr, (x, yy), v, size=SMALL - 2, outline=None)
    S.text(dr, (tx, ty + 40 + 34 * len(d.rounds) + 16), "suppressed: eligible cells within D_MIN of the new gaze (itself "
           "included)", size=SMALL - 4, fill=S.INK2, outline=None)
    S.text(dr, (tx, ty + 40 + 34 * len(d.rounds) + 40), "margin: selected score minus the best eligible score outside "
           "the tie set", size=SMALL - 4, fill=S.INK2, outline=None)
    return img


def nb1b_reference_comparison(d: Data) -> Image.Image:
    seeds = d.nb["seeds"]

    def after(img, dr, L, T):
        for e in seeds:
            g = d.gazes[e["nearest_gaze"] - 1]
            xs, ys = B.xy(e["yaw_deg"], e["pitch_deg"])
            xg, yg = B.xy(g["yaw_deg"], g["pitch_deg"])
            if abs(xs - xg) < PW / 2:
                S.dashed_line(dr, [(L + xs, T + ys), (L + xg, T + yg)], SEED_COLOR, width=2, dash=6, gap=5)
        for g in d.gazes:
            gaze_glyph(dr, g, L, T)
        for e in seeds:
            seed_glyph(dr, e, L, T)

    desc = [f"{e['seed']} {e['id']}: A {e['A']:.3g}, rank {e['rank_in_full_raster']:,} of {e['candidates']:,}, nearest gaze "
            f"{e['nearest_gaze']} at {e['nearest_gaze_deg']:.1f}°" for e in seeds]
    lines = ["hollow diamonds: the accepted NB1b queued seeds (P1, P2 primary; S1–S3 secondary), a range-derived reference; "
             "dashed: to the nearest RGB gaze; descriptive only",
             "   ".join(desc[:3]), "   ".join(desc[3:])]
    return pano(heat_layer(d), "REFERENCE · NB1b queued seeds in the RGB attention field",
                         lines, BADGES["nb1b-reference-comparison.png"], after=after,
                         legend=lambda img, dr, x, y: legend(img, dr, x, y, [("gaze", "RGB gaze 1–6"),
                                                                             ("seed", "NB1b queued seed (reference)")]))


def overview(d: Data) -> Image.Image:
    Wd, Hd = 3040, 2140
    img = Image.new("RGB", (Wd, Hd), S.SURFACE)
    dr = ImageDraw.Draw(img)
    S.text(dr, (40, 28), "Natural Bootstrap-1c · RGB candidate gaze", size=S.T_HUGE - 12, bold=True, outline=None)
    S.text(dr, (40, 100), "Did coarse RGB alone nominate plausible places for the eye to spend expensive binocular "
           "attention?", size=S.T_BODY, fill=S.INK2, outline=None)
    S.text(dr, (40, 134), "Selection read the RGB proxy only (no depth, no validity mask, no hypotheses, no Blender "
           "identity); K = 6 is an attention budget; nothing was executed.", size=S.T_BODY, fill=S.INK2, outline=None)
    xr = Wd - 40
    for b in BADGES["overview.png"]:
        xr = S.badge(img, xr, 34, b) - 10
    RW = 1440
    regions = [(40, 190, 860), (1560, 190, 860), (40, 1080, 1020), (1560, 1080, 1020)]
    titles = [("A · coarse spherical RGB (the only input)", [ORA]),
              ("B · center-surround attention field A(g)", [DER]),
              ("C · six RGB gazes, order 1–6, with D_MIN exclusion", [DER]),
              ("D · post-freeze reference: range / NB1a / NB1b", [REF])]
    for (rx, ry, rh), (t, bs) in zip(regions, titles):
        dr.rounded_rectangle([rx - 10, ry - 10, rx + RW + 10, ry + rh], radius=10, fill=S.PANEL, outline=S.GRID)
        S.text(dr, (rx + 4, ry + 4), t, size=S.T_HEAD, bold=True, outline=None)
        xr = rx + RW
        for b in bs:
            xr = S.badge(img, xr, ry + 4, b) - 10
        dr = ImageDraw.Draw(img)
    oy = 60
    (ax, ay, _), (bx, by, _), (cx, cy, _), (qx, qy, _) = regions
    # A: RGB only
    img.paste(Image.fromarray(B.up(d.srgb8, SC)), (ax, ay + oy))
    dr = ImageDraw.Draw(img)
    B.axes(dr, ax, ay + oy, PW, PH, words=True, ticks=False)
    S.text(dr, (ax, ay + oy + PH + 12), "720 × 360 (0.5°) 8-bit sRGB proxy of the accepted Breadth-1 render; converted "
           "to linear RGB for the score", size=SMALL, fill=S.INK2, outline=None)
    # B: attention field
    img.paste(Image.fromarray(heat_layer(d)), (bx, by + oy))
    dr = ImageDraw.Draw(img)
    for g in d.gazes:
        gaze_glyph(dr, g, bx, by + oy, label=False, r=8)
    B.axes(dr, bx, by + oy, PW, PH, words=True, ticks=False)
    sa = d.summ["attention_score"]
    S.text(dr, (bx, by + oy + PH + 12), f"6° center vs 6–12° surround, solid-angle weighted; median {sa['median']:.3g}, "
           f"p99 {sa['p99']:.3g}, max {sa['max']:.3g}; colour ∝ (A / p99.5)^0.7", size=SMALL, fill=S.INK2, outline=None)
    # C: the six gazes with their exclusion neighbourhoods
    img.paste(Image.fromarray(faded_rgb(d)), (cx, cy + oy))
    dr = ImageDraw.Draw(img)
    gaze_rings(dr, d, cx, cy + oy)
    for g in d.gazes:
        gaze_glyph(dr, g, cx, cy + oy, size=SMALL + 4, r=12)
    B.axes(dr, cx, cy + oy, PW, PH, words=True, ticks=False)
    S.text(dr, (cx, cy + oy + PH + 12), f"greedy spherical NMS; dashed: D_MIN = 2·R_FULL = {SP.D_MIN_DEG:.2f}°; solid: "
           f"R_FULL {SP.R_FULL_DEG:.2f}°; min separation {d.summ['min_pairwise_deg']:.2f}°", size=SMALL, fill=S.INK2,
           outline=None)
    for k, g in enumerate(d.gazes):
        S.text(dr, (cx + (k % 3) * 480, cy + oy + PH + 44 + 30 * (k // 3)),
               f"{g['rank']}: yaw {g['yaw_deg']:+.1f}°, pitch {g['pitch_deg']:+.1f}°, A {g['A']:.3g}", size=SMALL,
               bold=(k == 0), outline=None)
    # D: reference, muted
    img.paste(Image.fromarray(class_layer(d)), (qx, qy + oy))
    B.hatch_cells(img, (qx, qy + oy), ~d.valid, SC)
    dr = ImageDraw.Draw(img)
    for e in d.nb["seeds"]:
        seed_glyph(dr, e, qx, qy + oy)
    for g in d.gazes:
        gaze_glyph(dr, g, qx, qy + oy, r=10)
    B.axes(dr, qx, qy + oy, PW, PH, words=True, ticks=False)
    legend(img, dr, qx, qy + oy + PH + 10, [(c, NB1B_SHORT[c]) for c in NB.SP.CLASSES] + [("nogeom", "no range"),
                                                                                          ("seed", "NB1b seed")])
    dr = ImageDraw.Draw(img)
    for k, e in enumerate(d.ev["gazes"]):
        rng = f"{e['range_m']:.2f} m" if e["range_m"] is not None else "no range"
        txt = (f"{e['rank']}: {e['nb1a_hypothesis'] or '—'} · {NB1B_SHORT[e['nb1b_class']]} · {rng} · "
               f"{GAZE_SHORT[e['gaze_class']]} · {e['reference_at_gaze']['kind']}")
        S.text(dr, (qx + (k % 2) * 720, qy + oy + PH + 48 + 28 * (k // 2)), txt, size=SMALL - 2, fill=S.INK2, outline=None)
    agg = d.ev["aggregate"]
    S.text(dr, (qx, qy + oy + PH + 48 + 28 * 3 + 6),
           f"valid range {agg['valid_range']}/6 · distinct NB1a hypotheses {agg['distinct_nb1a_hypotheses']} · "
           f"FULL-safe {agg['gaze_class_counts']['GAZE_FULL_SAFE']} · CENTER-only {agg['gaze_class_counts']['GAZE_CENTER_ONLY_SAFE']}"
           f" · unsafe {agg['gaze_class_counts']['GAZE_UNSAFE']} · no range {agg['gaze_class_counts']['GAZE_NO_RANGE']}",
           size=SMALL - 1, bold=True, fill=S.INK2, outline=None)
    return img


# ------------------------------------------------------------------ entry
def render_all(run: Path):
    d = Data(run)
    return {"overview.png": overview(d), "rgb-input.png": rgb_input(d), "attention-map.png": attention_map(d),
            "candidate-gazes.png": candidate_gazes(d), "center-surround-examples.png": center_surround_examples(d),
            "candidate-crops.png": candidate_crops(d), "candidate-evaluation.png": candidate_evaluation(d),
            "attention-score-distribution.png": attention_score_distribution(d),
            "nb1b-reference-comparison.png": nb1b_reference_comparison(d)}, d


def png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=False, compress_level=6)
    return buf.getvalue()


def visualize(run: Path, vis: Path) -> dict:
    vis.mkdir(parents=True, exist_ok=True)
    figs, d = render_all(run)
    out = {}
    for name in FIGURES:
        (vis / name).write_bytes(png_bytes(figs[name]))
        out[name] = {"sha256": sha256(vis / name), "size_wh": list(figs[name].size), "truth_badges": BADGES[name]}
    manifest = {"schema": "NB1c-visuals-manifest-v1", "run": str(run), "sources": d.sources, "code": R.code_state(),
                "regenerate": f".venv/bin/python tools/natural_bootstrap/nb1c_run.py visualize --run {run} --visuals {vis}",
                "products": out,
                "glyphs": {"RGB gaze": "numbered ink crosshair (selection order; not executed)",
                           "exclusion": "dashed ring, radius D_MIN", "full core": "solid ring, radius R_FULL",
                           "receptive field": "dotted ring R_CENTER, thin ring R_SURROUND (tangent-plane views)",
                           "core": "square outline (tangent-plane views)",
                           "NB1b seed": "hollow brown diamond (reference only)", "no range": "hatched",
                           "attention": "cream-orange-wine ramp of (A / p99.5)^0.7"}}
    (vis / "visuals-manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    print(f"[nb1c] visualize: {len(FIGURES)} figures -> {vis}")
    return manifest
