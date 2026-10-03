"""Breadth-1: the persistent human-facing figures of the spherical glance.

Contract: docs/classroom-oracle/breadth-1-spherical-glance-contract.md, sections 6-7.  Reads only the
saved run outputs (``glance.npz``, ``range.npz``, ``components.npz`` and the JSON records) and draws with
the accepted Visual Language 1 style (``tools/visual_language/style.py``, read-only): truth badges with
their non-colour cues, Okabe-Ito colours, DejaVu fonts.  Breadth-1 glyphs (contract section 6):
- derived seed direction: an ink diamond with a white halo;
- accepted-25 membership: a solid ring around it;
- old Controller domain: a dashed ink rectangle.
Deterministic: the checker regenerates every PNG byte-identically.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import shutil
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "visual_language"))

import breadth1_spec as SP  # noqa: E402
import style as S  # noqa: E402  (Visual Language 1, read-only)

SCALE = 2
PW, PH = SP.WIDTH * SCALE, SP.HEIGHT * SCALE
REF, ORA, DER = SP.TRUTH_REFERENCE, SP.TRUTH_ORACLE, SP.TRUTH_DERIVED
ACC = S.OI_ORANGE          # accepted localized 25 (always with a ring / hatch and a label: contrast < 3:1)
OTHER = S.OI_BLUE          # other authored objects
RAMP_NEAR, RAMP_FAR = np.array([214, 229, 247]), np.array([8, 48, 107])   # Visual Language 1 depth reference
GRAY_LO, GRAY_HI = np.array([222, 222, 218]), np.array([40, 40, 40])
NO_GEOM = (247, 246, 242)
SMALL = 16
FIGURES = ["overview.png", "rgb-panorama.png", "range-panorama.png", "instance-panorama.png",
           "object-boundary-overlay.png", "seed-direction-panorama.png", "support-size-histogram.png",
           "support-vs-range.png"]
BADGES = {
    "overview.png": [REF, ORA, DER],
    "rgb-panorama.png": [REF],
    "range-panorama.png": [REF],
    "instance-panorama.png": [ORA, DER],
    "object-boundary-overlay.png": [REF, DER],
    "seed-direction-panorama.png": [DER, REF],
    "support-size-histogram.png": [DER],
    "support-vs-range.png": [DER],
}


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ------------------------------------------------------------------ data
class Data:
    def __init__(self, run: Path):
        self.run = run
        g = np.load(run / "glance.npz")
        r = np.load(run / "range.npz")
        self.rgb, self.inst, self.pos = g["rgb"], g["instance"], g["position_w"]
        self.rng, self.cls, self.weights = r["range_m"], r["cell_class"], r["cell_weights_sr"]
        self.comp = np.load(run / "components.npz")["component_ordinal"]
        self.stats = json.loads((run / "object-stats.json").read_text())["objects"]
        self.summary = json.loads((run / "summary.json").read_text())
        self.seeds = json.loads((run / "seed-directions.json").read_text())["seeds"]
        self.by_id = {o["instance_id"]: o for o in self.stats}
        self.ranked = sorted([o for o in self.stats if o["rank"]], key=lambda o: o["rank"])
        self.sources = {n: sha256(run / n) for n in ("glance.npz", "range.npz", "components.npz", "object-stats.json",
                                                    "summary.json", "seed-directions.json")}


def gamma_u8(rgb_linear: np.ndarray) -> np.ndarray:
    """Visual Language 1 display transform: clip to [0, 1], gamma 1/2.2."""
    return np.rint(np.power(np.clip(np.asarray(rgb_linear, np.float64), 0, 1), 1 / 2.2) * 255).astype(np.uint8)


def up(a: np.ndarray, s: int = SCALE) -> np.ndarray:
    return np.repeat(np.repeat(a, s, axis=0), s, axis=1)


def id_palette(ids: np.ndarray) -> np.ndarray:
    """Visual Language 1's deterministic instance colouring (generate_visual_language1.id_palette)."""
    h = (ids.astype(np.int64) * 2654435761) & 0xFFFFFFFF
    rgb = np.stack([(h >> 8) & 255, (h >> 16) & 255, (h >> 24) & 255], -1).astype(np.float32)
    rgb = 60 + rgb * (170 / 255)
    rgb[ids == 0] = 245
    return rgb.astype(np.uint8)


def boundary_mask(inst: np.ndarray, s: int = SCALE) -> np.ndarray:
    """Pixels on an edge between cells of different authored identity (longitude wraps)."""
    big = up(inst, s)
    b = np.zeros(big.shape, bool)
    right = np.roll(big, -1, axis=1)
    b |= big != right
    b[:-1] |= big[:-1] != big[1:]
    return b


def range_image(d: Data, s: int = SCALE) -> tuple[np.ndarray, tuple[float, float]]:
    geo = d.cls != 3
    lr = np.log(d.rng[geo])
    lo, hi = float(np.percentile(lr, 1)), float(np.percentile(lr, 99))
    t = np.zeros(d.rng.shape)
    t[geo] = np.clip((np.log(d.rng[geo]) - lo) / max(hi - lo, 1e-9), 0, 1)
    img = (RAMP_NEAR * (1 - t[..., None]) + RAMP_FAR * t[..., None]).astype(np.uint8)
    img[~geo] = NO_GEOM
    return up(img, s), (math.exp(lo), math.exp(hi))


def xy(yaw: float, pitch: float, w: int = PW, h: int = PH) -> tuple[float, float]:
    return (yaw + 180.0) / 360.0 * w, (90.0 - pitch) / 180.0 * h


# ------------------------------------------------------------------ drawing helpers
def hatch_cells(img: Image.Image, origin, mask_cells: np.ndarray, s: int, color=S.STIPPLE) -> None:
    if not mask_cells.any():
        return
    m = Image.fromarray((up(mask_cells, s) * 255).astype(np.uint8))
    full = Image.new("L", img.size, 0)
    full.paste(m, origin)
    S.hatch(img, [origin[0], origin[1], origin[0] + m.size[0], origin[1] + m.size[1]], color, spacing=8, width=1,
            mask=full)


def domain_rect(dr: ImageDraw.ImageDraw, ox: int, oy: int, w: int, h: int, label: bool = True) -> None:
    x0, y0 = xy(SP.DOMAIN_YAW_DEG[0], SP.DOMAIN_PITCH_DEG[1], w, h)
    x1, y1 = xy(SP.DOMAIN_YAW_DEG[1], SP.DOMAIN_PITCH_DEG[0], w, h)
    box = [ox + x0, oy + y0, ox + x1, oy + y1]
    S.dashed_rect(dr, box, S.WHITE, width=5, dash=12, gap=6)
    S.dashed_rect(dr, box, S.INK, width=3, dash=12, gap=6)
    if label:
        S.text(dr, (box[0], box[1] - 6), "old Controller domain ±25° × ±20°", size=SMALL, bold=True,
               plate=S.WHITE, anchor="ld")


def axes(dr: ImageDraw.ImageDraw, ox: int, oy: int, w: int, h: int, words: bool = True, ticks: bool = True) -> None:
    dr.rectangle([ox - 1, oy - 1, ox + w, oy + h], outline=S.INK2, width=1)
    for yaw in range(-150, 180, 30):
        x = ox + xy(yaw, 0, w, h)[0]
        dr.line([x, oy, x, oy + h], fill=(255, 255, 255), width=1)
    for pitch in (-60, -30, 0, 30, 60):
        y = oy + xy(0, pitch, w, h)[1]
        dr.line([ox, y, ox + w, y], fill=(255, 255, 255), width=1)
    if ticks:
        for yaw in range(-180, 181, 30):
            x = ox + xy(yaw, 0, w, h)[0]
            dr.line([x, oy + h, x, oy + h + 6], fill=S.INK2, width=1)
            S.text(dr, (x, oy + h + 8), f"{yaw}°", size=SMALL, fill=S.INK2, outline=None, anchor="ma")
        for pitch in range(-90, 91, 30):
            y = oy + xy(0, pitch, w, h)[1]
            dr.line([ox - 6, y, ox, y], fill=S.INK2, width=1)
            S.text(dr, (ox - 9, y), f"{pitch}°", size=SMALL, fill=S.INK2, outline=None, anchor="rm")
    if words:
        for yaw, word in ((-180, "behind"), (-90, "left"), (0, "front"), (90, "right"), (180, "behind")):
            x = ox + xy(yaw, 0, w, h)[0]
            S.text(dr, (min(max(x, ox + 30), ox + w - 30), oy - 4), word, size=SMALL, fill=S.INK2, outline=None,
                   anchor="md")


def diamond(dr: ImageDraw.ImageDraw, x: float, y: float, r: float = 6, accepted: bool = False) -> None:
    pts = [(x, y - r), (x + r, y), (x, y + r), (x - r, y)]
    halo = [(x, y - r - 2), (x + r + 2, y), (x, y + r + 2), (x - r - 2, y)]
    dr.polygon(halo, fill=S.WHITE)
    dr.polygon(pts, fill=S.INK)
    if accepted:
        R = r + 6
        dr.ellipse([x - R - 1, y - R - 1, x + R + 1, y + R + 1], outline=S.WHITE, width=5)
        dr.ellipse([x - R, y - R, x + R, y + R], outline=ACC, width=3)


def header(img: Image.Image, title: str, lines: list[str], badges: list[str], x0: int = 40, y0: int = 26,
           right: int | None = None) -> None:
    dr = ImageDraw.Draw(img)
    S.text(dr, (x0, y0), title, size=S.T_TITLE, bold=True, outline=None)
    for k, ln in enumerate(lines):
        S.text(dr, (x0, y0 + 44 + 28 * k), ln, size=S.T_SMALL, fill=S.INK2, outline=None)
    xr = (right if right is not None else img.size[0] - 40)
    for b in badges:
        xr = S.badge(img, xr, y0 + 2, b) - 10


def pano_figure(content: np.ndarray, title: str, lines: list[str], badges: list[str], legend=None,
                after=None, extra_right: int = 0) -> Image.Image:
    L, T, B = 110, 70 + 28 * len(lines) + 40, 120
    img = Image.new("RGB", (L + PW + 40 + extra_right, T + PH + B), S.SURFACE)
    img.paste(Image.fromarray(content), (L, T))
    dr = ImageDraw.Draw(img)
    if after:
        after(img, dr, L, T)
        dr = ImageDraw.Draw(img)
    axes(dr, L, T, PW, PH)
    header(img, title, lines, badges)
    S.text(dr, (L + PW / 2, T + PH + 40), "yaw (head frame, positive toward the right)", size=SMALL, fill=S.INK2,
           outline=None, anchor="ma")
    S.text(dr, (24, T + PH / 2), "pitch", size=SMALL, fill=S.INK2, outline=None, anchor="lm")
    if legend:
        legend(img, ImageDraw.Draw(img), L, T + PH + 70)
    return img


def legend_items(img: Image.Image, dr, x: int, y: int, items) -> None:
    for kind, label in items:
        if kind == "diamond":
            diamond(dr, x + 12, y + 11, 6)
        elif kind == "accepted":
            diamond(dr, x + 12, y + 11, 6, accepted=True)
        elif kind == "domain":
            S.dashed_rect(dr, [x, y + 2, x + 26, y + 20], S.INK, width=3, dash=7, gap=4)
        elif kind == "boundary":
            dr.line([x, y + 11, x + 26, y + 11], fill=S.INK, width=2)
        elif kind == "nogeom":
            dr.rectangle([x, y + 1, x + 26, y + 21], fill=NO_GEOM, outline=S.MUTED)
            S.hatch(img, [x, y + 1, x + 26, y + 21], S.STIPPLE, spacing=6, width=1)
            dr = ImageDraw.Draw(img)
        elif kind == "noncat":
            dr.rectangle([x, y + 1, x + 26, y + 21], fill=(245, 245, 245), outline=S.INK2, width=2)
        x0 = x + 36
        bb = S.text(dr, (x0, y + 11), label, size=SMALL, fill=S.INK, outline=None, anchor="lm")
        x = bb[2] + 30


# ------------------------------------------------------------------ figures
def rgb_panorama(d: Data) -> Image.Image:
    def after(img, dr, L, T):
        domain_rect(dr, L, T, PW, PH)

    return pano_figure(up(gamma_u8(d.rgb)), "RGB spherical glance — the Classroom from the fixed head",
                       ["Combined pass of the single canonical Blender render: 720 × 360 cells (0.5°), 512 spp, "
                        "full equirectangular sphere",
                        "reference imagery: not an observation used by any controller; no gaze, no foveation"],
                       BADGES["rgb-panorama.png"], after=after,
                       legend=lambda img, dr, x, y: legend_items(img, dr, x, y, [("domain", "old Controller domain (±25° × ±20°)")]))


def range_panorama(d: Data) -> Image.Image:
    img_arr, (lo, hi) = range_image(d)

    def after(img, dr, L, T):
        hatch_cells(img, (L, T), d.cls == 3, SCALE)
        domain_rect(ImageDraw.Draw(img), L, T, PW, PH, label=False)

    def legend(img, dr, x, y):
        legend_items(img, dr, x, y, [("nogeom", "no geometry (Object Index 0, Position 0)"),
                                     ("domain", "old Controller domain")])
        colorbar(img, x + 900, y + 2, 520, 20, lo, hi)

    return pano_figure(img_arr, "Range from the cyclopean head origin",
                       ["‖Position − head origin‖ from the same render's Position pass (never perspective depth); "
                        "log scale, light = near, dark = far",
                        f"colour limits: 1st–99th percentile of log range over geometric cells ({lo:.2f}–{hi:.2f} m)"],
                       BADGES["range-panorama.png"], after=after, legend=legend)


def colorbar(img: Image.Image, x: int, y: int, w: int, h: int, lo: float, hi: float) -> None:
    t = np.linspace(0, 1, w)[None, :, None]
    bar = (RAMP_NEAR * (1 - t) + RAMP_FAR * t).astype(np.uint8).repeat(h, axis=0)
    img.paste(Image.fromarray(bar), (x, y))
    dr = ImageDraw.Draw(img)
    dr.rectangle([x - 1, y - 1, x + w, y + h], outline=S.INK2)
    for m in (0.25, 0.5, 1, 2, 4, 8, 16, 32):
        if lo <= m <= hi:
            u = (math.log(m) - math.log(lo)) / (math.log(hi) - math.log(lo))
            dr.line([x + u * w, y + h, x + u * w, y + h + 5], fill=S.INK2)
            S.text(dr, (x + u * w, y + h + 6), f"{m:g} m", size=SMALL - 2, fill=S.INK2, outline=None, anchor="ma")


def instance_layer(d: Data, s: int = SCALE) -> np.ndarray:
    img = up(id_palette(d.inst), s)
    img[up(d.cls == 2, s)] = (245, 245, 245)
    img[boundary_mask(d.inst, s)] = S.INK
    return img


def label_ids(dr, d: Data, ox: int, oy: int, w: int, h: int, top: int, size: int = SMALL) -> None:
    seeds = {s["instance_id"]: s for s in d.seeds}
    for o in d.ranked[:top]:
        sd = seeds[o["instance_id"]]
        x, y = xy(sd["yaw_deg"], sd["pitch_deg"], w, h)
        S.text(dr, (ox + x, oy + y), str(o["instance_id"]), size=size, bold=True, plate=S.WHITE, anchor="mm")


def instance_panorama(d: Data) -> Image.Image:
    def after(img, dr, L, T):
        hatch_cells(img, (L, T), d.cls == 3, SCALE)
        dr = ImageDraw.Draw(img)
        label_ids(dr, d, L, T, PW, PH, 25)

    return pano_figure(instance_layer(d), "Authored Object Index — the 234-object accounting universe",
                       ["Blender Object Index pass (accepted Classroom-Oracle id assignment); one flat colour per authored "
                        "object, ink lines at identity changes",
                        "labels: catalog ids of the 25 largest visible supports, at their derived seed directions; "
                        "authored identity is not natural segmentation"],
                       BADGES["instance-panorama.png"], after=after,
                       legend=lambda img, dr, x, y: legend_items(img, dr, x, y, [
                           ("boundary", "authored-identity boundary (DERIVED)"),
                           ("noncat", "geometry without a catalog id (Object Index 0)"),
                           ("nogeom", "no geometry")]))


def boundary_overlay(d: Data) -> Image.Image:
    base = up(gamma_u8(d.rgb))
    base[boundary_mask(d.inst)] = S.INK
    return pano_figure(base, "Authored-object boundaries over the RGB glance",
                       ["where the Object Index changes between neighbouring cells (longitude wraps): a seam in the "
                        "Blender scene graph, not a perceptual edge",
                        "compare with the RGB/range coherence: authored segmentation and apparent coherence may disagree"],
                       BADGES["object-boundary-overlay.png"],
                       legend=lambda img, dr, x, y: legend_items(img, dr, x, y, [("boundary", "authored-identity boundary")]))


def seed_layer(d: Data, s: int = SCALE) -> np.ndarray:
    base = up(gamma_u8(d.rgb), s).astype(np.float32)
    base = 0.45 * base + 0.55 * 255
    b = boundary_mask(d.inst, s)
    base[b] = (150, 150, 150)
    return base.astype(np.uint8)


def draw_seeds(dr, d: Data, ox: int, oy: int, w: int, h: int, r: float) -> None:
    for sd in sorted(d.seeds, key=lambda s: s["in_accepted_localized_25"]):
        x, y = xy(sd["yaw_deg"], sd["pitch_deg"], w, h)
        diamond(dr, ox + x, oy + y, r, accepted=sd["in_accepted_localized_25"])


def seed_panorama(d: Data) -> Image.Image:
    table_w = 470

    def after(img, dr, L, T):
        domain_rect(dr, L, T, PW, PH)
        draw_seeds(dr, d, L, T, PW, PH, 6)
        label_ids(dr, d, L, T + 18, PW, PH, 25, size=SMALL - 3)
        x0 = L + PW + 60
        S.text(dr, (x0, T - 4), "25 largest visible supports", size=S.T_SMALL, bold=True, outline=None, anchor="ld")
        for k, o in enumerate(d.ranked[:25]):
            y = T + 8 + 28 * k
            name = o["object_name"] if len(o["object_name"]) <= 18 else o["object_name"][:17] + "…"
            mark = "●" if o["in_accepted_localized_25"] else " "
            S.text(dr, (x0, y), f"{o['rank']:>2}  {o['instance_id']:>3}  {name}", size=SMALL, fill=S.INK, outline=None)
            S.text(dr, (x0 + table_w - 70, y), f"{o['solid_angle_sr']:.3f} sr {mark}", size=SMALL, fill=S.INK2,
                   outline=None, anchor="ra")
        S.text(dr, (x0, T + 8 + 28 * 25 + 6), "rank · id · authored name · solid angle; ● accepted 25", size=SMALL - 2,
               fill=S.INK2, outline=None)

    return pano_figure(seed_layer(d), "Representative DERIVED seed directions — one per visible authored object",
                       ["largest seam-aware 8-connected component; solid-angle-weighted mean direction; the nearest "
                        "actual support cell (always on observed support)",
                        "analysis only: no seed causes an observation; numbers are catalog ids (25 largest supports)"],
                       BADGES["seed-direction-panorama.png"], after=after, extra_right=table_w,
                       legend=lambda img, dr, x, y: legend_items(img, dr, x, y, [
                           ("diamond", "derived seed direction"), ("accepted", "in the accepted localized 25"),
                           ("domain", "old Controller domain"), ("boundary", "authored boundary")]))


# ------------------------------------------------------------------ charts
def log_x(v: float, lo: float, hi: float, x0: float, w: float) -> float:
    return x0 + (math.log10(v) - math.log10(lo)) / (math.log10(hi) - math.log10(lo)) * w


def support_histogram(d: Data) -> Image.Image:
    W, H = 1600, 980
    img = Image.new("RGB", (W, H), S.SURFACE)
    dr = ImageDraw.Draw(img)
    header(img, "How much of the sphere does each authored object occupy?",
           ["visible solid angle per authored object, in the bins declared before the run (edges 10^(k/2) sr); "
            "the leftmost bar counts objects with no first-hit cell",
            "stacked: other authored objects (blue) and the accepted localized 25 (orange, hatched); "
            "counts are objects, not cells"], BADGES["support-size-histogram.png"])
    edges = SP.SOLID_ANGLE_EDGES_SR
    vis = [o for o in d.stats if o["visible_cells"]]
    nbins = len(edges) - 1
    acc_c, oth_c = np.zeros(nbins + 1, int), np.zeros(nbins + 1, int)   # the extra slot: >= the last edge
    for o in vis:
        k = int(np.searchsorted(edges, o["solid_angle_sr"], side="right") - 1)
        if k < 0:
            raise ValueError("support below the first declared edge (impossible: one pole cell is 3.3e-7 sr)")
        (acc_c if o["in_accepted_localized_25"] else oth_c)[min(k, nbins)] += 1
    nf_acc = sum(1 for o in d.stats if not o["visible_cells"] and o["in_accepted_localized_25"])
    nf_oth = sum(1 for o in d.stats if not o["visible_cells"] and not o["in_accepted_localized_25"])
    x0, y0, pw, ph = 230, 200, 1200, 600
    gap_w = 110
    bars = [("0", nf_oth, nf_acc)] + [(None, oth_c[k], acc_c[k]) for k in range(nbins + 1)]
    ymax = max(1, max(a + b for _, a, b in bars))
    step = 10 ** math.floor(math.log10(ymax)) if ymax >= 10 else 1
    ytop = math.ceil(ymax / step) * step
    for v in np.arange(0, ytop + 0.5 * step, step):
        y = y0 + ph - v / ytop * ph
        dr.line([x0 - gap_w, y, x0 + pw, y], fill=S.GRID, width=1)
        S.text(dr, (x0 - gap_w - 10, y), f"{int(v)}", size=SMALL, fill=S.INK2, outline=None, anchor="rm")
    bw = pw / nbins
    for k, (lab, oth, acc) in enumerate(bars):
        if k == 0:
            bx0, bx1 = x0 - gap_w + 20, x0 - 30
        elif k == nbins + 1:
            bx0, bx1 = x0 + pw + 40, x0 + pw + 40 + bw - 8
        else:
            bx0, bx1 = x0 + (k - 1) * bw + 4, x0 + k * bw - 4
        yb = y0 + ph
        for n, col, hat in ((oth, OTHER, False), (acc, ACC, True)):
            if n:
                yt = yb - n / ytop * ph
                dr.rounded_rectangle([bx0, yt, bx1, yb - 2], radius=4, fill=col)
                if hat:
                    S.hatch(img, [bx0, yt, bx1, yb - 2], S.WHITE, spacing=7, width=2)
                    dr = ImageDraw.Draw(img)
                yb = yt - 2
        if oth + acc:
            S.text(dr, ((bx0 + bx1) / 2, yb - 6), f"{oth + acc}", size=SMALL, bold=True, outline=None, anchor="md")
    if nf_oth + nf_acc == 0:
        S.text(dr, ((x0 - gap_w + 20 + x0 - 30) / 2, y0 + ph - 6), "0", size=SMALL, bold=True, outline=None, anchor="md")
    for k in range(nbins + 1):
        x = x0 + k * bw
        if k % 2 == 0:
            e = edges[k]
            dr.line([x, y0 + ph, x, y0 + ph + 6], fill=S.INK2)
            S.text(dr, (x, y0 + ph + 10), f"1e{int(round(math.log10(e)))}", size=SMALL, fill=S.INK2, outline=None, anchor="ma")
    S.text(dr, ((x0 - gap_w + x0) / 2 + 5, y0 + ph + 10), "none", size=SMALL, fill=S.INK2, outline=None, anchor="ma")
    S.text(dr, (x0 + pw + 40 + bw / 2, y0 + ph + 10), f"≥{edges[-1]:g}", size=SMALL, fill=S.INK2, outline=None,
           anchor="ma")
    for v, lab in ((float(d.weights[SP.HEIGHT // 2]), "1 cell at the equator"), (float(d.weights[0]), "1 cell at the pole row"),
                   (4 * math.pi, "4π")):
        if edges[0] <= v <= edges[-1]:
            x = log_x(v, edges[0], edges[-1], x0, pw)
            S.dashed_line(dr, [(x, y0), (x, y0 + ph)], S.MUTED, width=1, dash=5, gap=5)
            S.text(dr, (x + 4, y0 + 4), lab, size=SMALL - 2, fill=S.INK2, outline=None)
    S.text(dr, (x0 + pw / 2, y0 + ph + 44), "visible solid angle per object (steradian, log scale)", size=S.T_SMALL,
           fill=S.INK2, outline=None, anchor="ma")
    S.text(dr, (40, y0 + ph / 2), "objects", size=S.T_SMALL, fill=S.INK2, outline=None, anchor="lm")
    s = d.summary
    lx, ly = x0, H - 90
    dr.rounded_rectangle([lx, ly, lx + 26, ly + 20], radius=4, fill=OTHER)
    S.text(dr, (lx + 36, ly + 10), f"other authored objects ({s['visible_at_0p5_deg'] - s['accepted_localized_25']['visible']} visible)",
           size=SMALL, outline=None, anchor="lm")
    lx2 = lx + 520
    dr.rounded_rectangle([lx2, ly, lx2 + 26, ly + 20], radius=4, fill=ACC)
    S.hatch(img, [lx2, ly, lx2 + 26, ly + 20], S.WHITE, spacing=7, width=2)
    dr = ImageDraw.Draw(img)
    S.text(dr, (lx2 + 36, ly + 10), f"accepted localized 25 ({s['accepted_localized_25']['visible']} visible)",
           size=SMALL, outline=None, anchor="lm")
    S.text(dr, (lx2 + 560, ly + 10), f"no first hit at 0.5°: {s['no_first_hit_at_0p5_deg']} of {s['catalog_total']}",
           size=SMALL, bold=True, outline=None, anchor="lm")
    return img


def support_vs_range(d: Data) -> Image.Image:
    W, H = 1600, 1000
    img = Image.new("RGB", (W, H), S.SURFACE)
    dr = ImageDraw.Draw(img)
    header(img, "Support versus distance — one mark per visible authored object",
           ["x: median radial range of the object's visible cells (m, log scale); y: visible solid angle (sr, log scale)",
            "orange diamond with ring: accepted localized 25; blue circle: other authored objects; names: 8 largest supports"],
           BADGES["support-vs-range.png"])
    vis = [o for o in d.stats if o["visible_cells"]]
    x0, y0, pw, ph = 200, 190, 1300, 640
    xs = [o["range_m"]["median"] for o in vis]
    ys = [o["solid_angle_sr"] for o in vis]
    xlo = 2.0 ** math.floor(math.log2(min(xs))) if xs else 0.25
    xhi = 2.0 ** math.ceil(math.log2(max(xs))) if xs else 32
    if xhi <= xlo:
        xhi = xlo * 2
    ylo, yhi = SP.SOLID_ANGLE_EDGES_SR[0], SP.SOLID_ANGLE_EDGES_SR[-1]

    def px(v):
        return x0 + (math.log2(v) - math.log2(xlo)) / (math.log2(xhi) - math.log2(xlo)) * pw

    def py(v):
        return y0 + ph - (math.log10(v) - math.log10(ylo)) / (math.log10(yhi) - math.log10(ylo)) * ph

    dr.rectangle([x0, y0, x0 + pw, y0 + ph], outline=S.INK2)
    m = xlo
    while m <= xhi * 1.0001:
        dr.line([px(m), y0, px(m), y0 + ph], fill=S.GRID)
        S.text(dr, (px(m), y0 + ph + 8), f"{m:g}", size=SMALL, fill=S.INK2, outline=None, anchor="ma")
        m *= 2
    for k in range(-7, 2):
        v = 10.0 ** k
        dr.line([x0, py(v), x0 + pw, py(v)], fill=S.GRID)
        S.text(dr, (x0 - 10, py(v)), f"1e{k}", size=SMALL, fill=S.INK2, outline=None, anchor="rm")
    for o in sorted(vis, key=lambda o: o["in_accepted_localized_25"]):
        x, y = px(o["range_m"]["median"]), py(o["solid_angle_sr"])
        if o["in_accepted_localized_25"]:
            r = 8
            dr.polygon([(x, y - r), (x + r, y), (x, y + r), (x - r, y)], fill=ACC, outline=S.INK)
            dr.ellipse([x - r - 5, y - r - 5, x + r + 5, y + r + 5], outline=S.INK, width=2)
        else:
            dr.ellipse([x - 6, y - 6, x + 6, y + 6], outline=OTHER, width=2)
    for o in d.ranked[:8]:
        x, y = px(o["range_m"]["median"]), py(o["solid_angle_sr"])
        S.text(dr, (x + 14, y - 12), f"{o['object_name']} ({o['instance_id']})", size=SMALL - 1, plate=S.WHITE, anchor="ld")
    S.text(dr, (x0 + pw / 2, y0 + ph + 40), "median radial range from the head origin (m, log scale)", size=S.T_SMALL,
           fill=S.INK2, outline=None, anchor="ma")
    S.text(dr, (30, y0 + ph / 2), "sr", size=S.T_SMALL, fill=S.INK2, outline=None, anchor="lm")
    ly = H - 80
    dr.polygon([(x0 + 10, ly), (x0 + 18, ly + 8), (x0 + 10, ly + 16), (x0 + 2, ly + 8)], fill=ACC, outline=S.INK)
    dr.ellipse([x0 - 3, ly - 5, x0 + 23, ly + 21], outline=S.INK, width=2)
    S.text(dr, (x0 + 36, ly + 8), "accepted localized 25", size=SMALL, outline=None, anchor="lm")
    dr.ellipse([x0 + 330, ly + 2, x0 + 342, ly + 14], outline=OTHER, width=2)
    S.text(dr, (x0 + 356, ly + 8), "other authored objects", size=SMALL, outline=None, anchor="lm")
    return img


# ------------------------------------------------------------------ overview
def waffle(img: Image.Image, d: Data, x: int, y: int, cell: int = 30) -> tuple[int, int]:
    dr = ImageDraw.Draw(img)
    order = d.ranked + sorted([o for o in d.stats if not o["visible_cells"]], key=lambda o: o["instance_id"])
    cols = 18
    vis_omega = [o["solid_angle_sr"] for o in d.ranked]
    lo = math.log10(min(vis_omega)) if vis_omega else 0
    hi = math.log10(max(vis_omega)) if vis_omega else 1
    for k, o in enumerate(order):
        r, c = divmod(k, cols)
        bx, by = x + c * cell, y + r * cell
        box = [bx + 2, by + 2, bx + cell - 2, by + cell - 2]
        if o["visible_cells"]:
            t = (math.log10(o["solid_angle_sr"]) - lo) / max(hi - lo, 1e-9)
            col = tuple(int(v) for v in GRAY_LO * (1 - t) + GRAY_HI * t)
            dr.rectangle(box, fill=col)
        else:
            dr.rectangle(box, fill=S.WHITE)
            S.dashed_rect(dr, box, S.MUTED, width=1, dash=3, gap=3)
        if o["in_accepted_localized_25"]:
            dr.rectangle([bx, by, bx + cell, by + cell], outline=ACC, width=3)
    rows = math.ceil(len(order) / cols)
    return x + cols * cell, y + rows * cell


def overview(d: Data) -> Image.Image:
    W, H = 3040, 2060
    img = Image.new("RGB", (W, H), S.SURFACE)
    dr = ImageDraw.Draw(img)
    s = d.summary
    S.text(dr, (40, 28), "Breadth-1 · Classroom-234 spherical glance", size=S.T_HUGE - 12, bold=True, outline=None)
    S.text(dr, (40, 100), "One 720 × 360 (0.5°) full-sphere Blender observation from the fixed cyclopean head origin, "
           "before active foveation — no gaze, no controller, no foveation, no stereo growth.", size=S.T_BODY,
           fill=S.INK2, outline=None)
    S.text(dr, (40, 134), "The 234 authored Blender objects are the accounting universe, not natural perceptual objects. "
           "A missing first hit is a sampling outcome, not a claim of occlusion.", size=S.T_BODY, fill=S.INK2, outline=None)
    xr = W - 40
    for b in BADGES["overview.png"]:
        xr = S.badge(img, xr, 34, b) - 10
    regions = [(40, 190), (1560, 190), (40, 1120), (1560, 1120)]
    RW, RH = 1440, 900
    titles = [("RGB spherical glance", [REF]), ("Range from the head origin (log)", [REF]),
              ("Authored Object Index and boundaries", [ORA, DER]),
              ("Accounting and representative seed directions", [DER])]
    for (rx, ry), (t, bs) in zip(regions, titles):
        dr.rounded_rectangle([rx - 10, ry - 10, rx + RW + 10, ry + RH], radius=10, fill=S.PANEL, outline=S.GRID)
        S.text(dr, (rx + 4, ry + 4), t, size=S.T_HEAD, bold=True, outline=None)
        xr = rx + RW
        for b in bs:
            xr = S.badge(img, xr, ry + 4, b) - 10
        dr = ImageDraw.Draw(img)
    oy = 70
    (r1x, r1y), (r2x, r2y), (r3x, r3y), (r4x, r4y) = regions
    img.paste(Image.fromarray(up(gamma_u8(d.rgb))), (r1x, r1y + oy))
    domain_rect(ImageDraw.Draw(img), r1x, r1y + oy, PW, PH)
    rimg, (lo, hi) = range_image(d)
    img.paste(Image.fromarray(rimg), (r2x, r2y + oy))
    hatch_cells(img, (r2x, r2y + oy), d.cls == 3, SCALE)
    img.paste(Image.fromarray(instance_layer(d)), (r3x, r3y + oy))
    hatch_cells(img, (r3x, r3y + oy), d.cls == 3, SCALE)
    dr = ImageDraw.Draw(img)
    label_ids(dr, d, r3x, r3y + oy, PW, PH, 15)
    for rx, ry in regions[:3]:
        axes(dr, rx, ry + oy, PW, PH, words=True, ticks=False)
        for yaw in (-180, -90, 0, 90, 180):
            x = rx + xy(yaw, 0)[0]
            S.text(dr, (min(max(x, rx + 20), rx + PW - 20), ry + oy + PH + 6), f"{yaw}°", size=SMALL, fill=S.INK2,
                   outline=None, anchor="ma")
    S.text(dr, (r1x, r1y + oy + PH + 34), "Combined pass, 512 spp; dashed: old Controller domain ±25° × ±20°",
           size=SMALL, fill=S.INK2, outline=None)
    S.text(dr, (r2x, r2y + oy + PH + 34), "from the Position pass; light near, dark far; hatched: no geometry",
           size=SMALL, fill=S.INK2, outline=None)
    colorbar(img, r2x + 880, r2y + oy + PH + 34, 520, 18, lo, hi)
    dr = ImageDraw.Draw(img)
    S.text(dr, (r3x, r3y + oy + PH + 34), "one colour per authored object; ink lines: identity changes; "
           "numbers: catalog ids of the 15 largest supports", size=SMALL, fill=S.INK2, outline=None)

    # region 4: seeds mini-panorama, accounting waffle, key numbers
    sx, sy = r4x, r4y + oy
    img.paste(Image.fromarray(seed_layer(d, 1)), (sx, sy))
    dr = ImageDraw.Draw(img)
    dr.rectangle([sx - 1, sy - 1, sx + SP.WIDTH, sy + SP.HEIGHT], outline=S.INK2)
    domain_rect(dr, sx, sy, SP.WIDTH, SP.HEIGHT, label=False)
    draw_seeds(dr, d, sx, sy, SP.WIDTH, SP.HEIGHT, 4)
    S.text(dr, (sx, sy + SP.HEIGHT + 8), "one derived seed per visible object (ring: accepted 25); analysis only",
           size=SMALL, fill=S.INK2, outline=None)
    acc = s["accepted_localized_25"]
    dom = s["old_controller_domain"]
    lines = [
        ("visible at 0.5°", f"{s['visible_at_0p5_deg']}"),
        ("no first hit at 0.5°", f"{s['no_first_hit_at_0p5_deg']}"),
        ("visible with >1 component", f"{s['visible_with_multiple_components']}"),
        ("accepted 25 visible / not", f"{acc['visible']} / {len(acc['no_first_hit'])}"),
        ("visible, not in the accepted 25", f"{acc['visible_outside_accepted_25']}"),
        ("visible, entirely outside old domain", f"{dom['visible_entirely_outside']}"),
    ]
    ky = sy + SP.HEIGHT + 50
    for k, (lab, val) in enumerate(lines):
        S.text(dr, (sx, ky + 34 * k), lab, size=S.T_SMALL, fill=S.INK2, outline=None)
        S.text(dr, (sx + 700, ky + 34 * k), val, size=S.T_SMALL, bold=True, outline=None, anchor="ra")
    tk = s["top_k_cumulative_support"]
    S.text(dr, (sx, ky + 34 * 6 + 12), "largest K objects cover (of 4π): " + "   ".join(
        f"K={k}: {100 * tk[str(k)]['fraction_of_4pi']:.1f}%" for k in SP.TOP_K), size=S.T_SMALL, outline=None)
    wx, wy = r4x + 780, r4y + oy + 50
    S.text(dr, (wx, r4y + oy), f"{s['catalog_total']} = {s['visible_at_0p5_deg']} visible + "
           f"{s['no_first_hit_at_0p5_deg']} no first hit", size=S.T_HEAD + 2, bold=True, outline=None)
    ex, ey = waffle(img, d, wx, wy, 30)
    dr = ImageDraw.Draw(img)
    ly = ey + 18
    dr.rectangle([wx, ly, wx + 22, ly + 22], fill=tuple(int(v) for v in GRAY_HI))
    S.text(dr, (wx + 32, ly + 11), "visible (darker = larger solid angle), by rank", size=SMALL, outline=None, anchor="lm")
    dr.rectangle([wx, ly + 34, wx + 22, ly + 56], fill=S.WHITE)
    S.dashed_rect(dr, [wx, ly + 34, wx + 22, ly + 56], S.MUTED, width=1, dash=3, gap=3)
    S.text(dr, (wx + 32, ly + 45), "no first-hit cell at 0.5°", size=SMALL, outline=None, anchor="lm")
    dr.rectangle([wx, ly + 68, wx + 22, ly + 90], outline=ACC, width=3)
    S.text(dr, (wx + 32, ly + 79), "accepted localized 25 (Controller-02)", size=SMALL, outline=None, anchor="lm")
    S.text(dr, (wx, ly + 104), "one square per catalog object (18 × 13 = 234)", size=SMALL, fill=S.INK2, outline=None)
    return img


# ------------------------------------------------------------------ entry
def render_all(run: Path) -> dict[str, Image.Image]:
    d = Data(run)
    return {"overview.png": overview(d), "rgb-panorama.png": rgb_panorama(d), "range-panorama.png": range_panorama(d),
            "instance-panorama.png": instance_panorama(d), "object-boundary-overlay.png": boundary_overlay(d),
            "seed-direction-panorama.png": seed_panorama(d), "support-size-histogram.png": support_histogram(d),
            "support-vs-range.png": support_vs_range(d)}, d


def png_bytes(img: Image.Image) -> bytes:
    import io
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
    shutil.copyfile(run / "global-point-cloud.ply", vis / "global-point-cloud.ply")
    out["global-point-cloud.ply"] = {"sha256": sha256(vis / "global-point-cloud.ply"),
                                     "truth_badges": [REF, ORA], "copy_of": str(run / "global-point-cloud.ply")}
    manifest = {"schema": "Breadth1-visuals-manifest-v1", "run": str(run), "sources": d.sources,
                "regenerate": f".venv/bin/python tools/classroom_oracle/breadth1_glance.py visualize --run {run} --visuals {vis}",
                "products": out,
                "glyphs": {"derived seed direction": "ink diamond with white halo",
                           "accepted-25 membership": "solid ring around the diamond (orange) / orange square outline / hatched bar",
                           "old Controller domain": "dashed ink rectangle",
                           "authored boundary": "thin ink line"}}
    (vis / "visuals-manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    print(f"[breadth1] visualize: {len(FIGURES)} figures + PLY -> {vis}")
    return manifest
