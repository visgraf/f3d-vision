"""Natural Bootstrap-1a: the persistent human-facing figures.

Contract: docs/natural-bootstrap/nb1a-range-connectivity-contract.md, section 9.  Reads only saved run
outputs.  Draws with the accepted Visual Language 1 style and the accepted Breadth-1 panorama helpers,
both read-only.  The natural decomposition is the subject; authored identity is the (secondary) reference.
Glyphs:
- ink diamond: derived seed (larger with interior clearance; singletons are small dots);
- thin solid ink: natural boundary;
- hatched: no geometry;
- thin brown: authored reference boundary (evaluation panels only).
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
import nb1a_spec as SP  # noqa: E402
import style as S  # noqa: E402  (Visual Language 1, read-only)

ORA, DER, REF = SP.TRUTH_ORACLE, SP.TRUTH_DERIVED, SP.TRUTH_REFERENCE
SC = 2
PW, PH = SP.WIDTH * SC, SP.HEIGHT * SC
SMALL = 16
SINGLE = S.OI_ORANGE      # singleton hypotheses in charts (always labelled / hatched: contrast < 3:1)
MULTI = S.OI_BLUE         # multi-cell hypotheses in charts
FIGURES = ["overview.png", "range-input.png", "continuity-boundaries.png", "hypothesis-panorama.png",
           "seed-panorama.png", "hypothesis-support-histogram.png", "interior-clearance-histogram.png",
           "overlap-matrix.png", "rgb-edge-contrast.png"]
BADGES = {
    "overview.png": [ORA, DER, REF], "range-input.png": [ORA], "continuity-boundaries.png": [DER, ORA],
    "hypothesis-panorama.png": [DER], "seed-panorama.png": [DER], "hypothesis-support-histogram.png": [DER],
    "interior-clearance-histogram.png": [DER], "overlap-matrix.png": [REF], "rgb-edge-contrast.png": [DER, ORA],
}


def sha256(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class Data:
    SOURCES = ["input/range-sensory.npz", "input/rgb-sensory.npz", "discovery/hypothesis-raster.npz",
               "discovery/continuity-edges.npz", "discovery/hypotheses.json", "discovery/discovery-summary.json",
               "evaluation/overlap-summary.json", "evaluation/rgb-edge-diagnostics.json",
               "evaluation/rgb-edge-contrast.npz", "evaluation/reference-cells.npz"]

    def __init__(self, run: Path):
        self.run = run
        with np.load(run / "input/range-sensory.npz") as z:
            self.rng, self.valid = z["range_m"], z["valid_mask"]
        with np.load(run / "input/rgb-sensory.npz") as z:
            self.srgb8 = z["srgb8"]
        with np.load(run / "discovery/hypothesis-raster.npz") as z:
            self.labels, self.bnd, self.clr = z["labels"], z["boundary"], z["clearance_rad"]
        with np.load(run / "discovery/continuity-edges.npz") as z:
            self.ea, self.eb, self.ret = z["a"], z["b"], z["retained"]
        self.hyps = json.loads((run / "discovery/hypotheses.json").read_text())["hypotheses"]
        self.summ = json.loads((run / "discovery/discovery-summary.json").read_text())
        self.ov = json.loads((run / "evaluation/overlap-summary.json").read_text())
        self.rgbd = json.loads((run / "evaluation/rgb-edge-diagnostics.json").read_text())
        with np.load(run / "evaluation/rgb-edge-contrast.npz") as z:
            self.intra_max = z["intra_max"]
        with np.load(run / "evaluation/reference-cells.npz") as z:   # REFERENCE / EVALUATION (post-freeze)
            self.oid, self.o0 = z["object_index"], z["o0_mask"]
        self.sources = {n: sha256(run / n) for n in self.SOURCES}


# ------------------------------------------------------------------ layers
def range_layer(d: Data, s: int = SC) -> tuple[np.ndarray, tuple[float, float]]:
    lr = np.log(d.rng[d.valid])
    lo, hi = float(np.percentile(lr, 1)), float(np.percentile(lr, 99))
    t = np.zeros(d.rng.shape)
    t[d.valid] = np.clip((np.log(d.rng[d.valid]) - lo) / max(hi - lo, 1e-9), 0, 1)
    img = (B.RAMP_NEAR * (1 - t[..., None]) + B.RAMP_FAR * t[..., None]).astype(np.uint8)
    img[~d.valid] = B.NO_GEOM
    return B.up(img, s), (math.exp(lo), math.exp(hi))


def cut_mask(d: Data, s: int = SC, which: str = "cut") -> np.ndarray:
    """Pixels on the shared border (or corner) of every cut continuity edge."""
    m = np.zeros((SP.HEIGHT * s, SP.WIDTH * s), bool)
    sel = ~d.ret if which == "cut" else d.ret
    a, b = d.ea[sel].astype(np.int64), d.eb[sel].astype(np.int64)
    ra, ca, rb, cb = a // SP.WIDTH, a % SP.WIDTH, b // SP.WIDTH, b % SP.WIDTH
    dc = (cb - ca + 1) % SP.WIDTH - 1
    dr = rb - ra
    h = (dr == 0)
    for k in range(s):
        m[ra[h] * s + k, ((ca[h] + 1) * s - 1) % (SP.WIDTH * s)] = True
    v = (dr == 1) & (dc == 0)
    for k in range(s):
        m[(ra[v] + 1) * s - 1, ca[v] * s + k] = True
    dp = (dr == 1) & (dc == 1)
    m[(ra[dp] + 1) * s - 1, ((ca[dp] + 1) * s - 1) % (SP.WIDTH * s)] = True
    dm = (dr == 1) & (dc == -1)
    m[(ra[dm] + 1) * s - 1, ca[dm] * s] = True
    return m


def valid_border(d: Data, s: int = SC) -> np.ndarray:
    return B.boundary_mask(d.valid.astype(np.int64), s)


def hyp_layer(d: Data, s: int = SC, pale: float = 0.0) -> np.ndarray:
    col = B.id_palette(d.labels.astype(np.int64) * 7919 + 13).astype(np.float32)
    col[~d.valid] = B.NO_GEOM
    if pale:
        col = (1 - pale) * col + pale * 255
    img = B.up(col.astype(np.uint8), s)
    img[B.boundary_mask(d.labels.astype(np.int64), s)] = S.INK
    return img


def seed_radius(h: dict) -> float:
    c = h["max_interior_clearance_deg"]
    if h["cells"] == 1:
        return 0.0
    return 3.0 + 1.6 * math.sqrt(max(c or 0.0, 0.0)) if c is not None else 6.0


def draw_seeds(dr, d: Data, ox: int, oy: int, w: int, h: int, scale: float = 1.0, labels: int = 0) -> None:
    for hp in reversed(d.hyps):
        s = hp["seed"]
        x, y = B.xy(s["yaw_deg"], s["pitch_deg"], w, h)
        x, y = ox + x, oy + y
        r = seed_radius(hp) * scale
        if r <= 0:
            dr.rectangle([x - 0.8, y - 0.8, x + 0.8, y + 0.8], fill=S.INK)
        else:
            B.diamond(dr, x, y, max(r, 2.5))
    for hp in d.hyps[:labels]:
        s = hp["seed"]
        x, y = B.xy(s["yaw_deg"], s["pitch_deg"], w, h)
        S.text(dr, (ox + x, oy + y + seed_radius(hp) * scale + 10), hp["id"], size=SMALL - 3, bold=True,
               plate=S.WHITE, anchor="mm")


def legend(img, dr, x, y, items) -> None:
    for kind, label in items:
        if kind == "cut":
            dr.line([x, y + 11, x + 26, y + 11], fill=S.INK, width=2)
        elif kind == "ref":
            dr.line([x, y + 11, x + 26, y + 11], fill=S.REF_BROWN, width=2)
        elif kind == "nogeom":
            dr.rectangle([x, y + 1, x + 26, y + 21], fill=B.NO_GEOM, outline=S.MUTED)
            S.hatch(img, [x, y + 1, x + 26, y + 21], S.STIPPLE, spacing=6, width=1)
            dr = ImageDraw.Draw(img)
        elif kind == "seed":
            B.diamond(dr, x + 13, y + 11, 7)
        elif kind == "dot":
            dr.rectangle([x + 12, y + 10, x + 14, y + 12], fill=S.INK)
        elif kind == "o0":
            dr.rectangle([x, y + 1, x + 26, y + 21], fill=(250, 240, 222), outline=S.REF_BROWN)
            S.hatch(img, [x, y + 1, x + 26, y + 21], (200, 160, 100), spacing=5, width=1)
            dr = ImageDraw.Draw(img)
        bb = S.text(dr, (x + 36, y + 11), label, size=SMALL, outline=None, anchor="lm")
        x = bb[2] + 30


def pano(content, title, lines, badges, after=None, leg=None, extra_right: int = 0) -> Image.Image:
    return B.pano_figure(content, title, lines, badges, legend=leg, after=after, extra_right=extra_right)


# ------------------------------------------------------------------ figures
def range_input(d: Data) -> Image.Image:
    rimg, (lo, hi) = range_layer(d)
    W, T = 110 + PW + 40, 150
    img = Image.new("RGB", (W, T + 2 * (PH + 70) + 90), S.SURFACE)
    B.header(img, "Sensory proxy: RGB and radial range from the fixed head",
             ["controlled proxy derived from the Blender Combined + Position passes of the accepted Breadth-1 "
              "observation (not stereo); discovery reads only range + validity",
              "RGB (top) is diagnostic / visual only; range (bottom) is log-scaled, light = near"], BADGES["range-input.png"])
    img.paste(Image.fromarray(B.up(d.srgb8)), (110, T))
    img.paste(Image.fromarray(rimg), (110, T + PH + 70))
    B.hatch_cells(img, (110, T + PH + 70), ~d.valid, SC)
    dr = ImageDraw.Draw(img)
    B.axes(dr, 110, T, PW, PH)
    B.axes(dr, 110, T + PH + 70, PW, PH)
    y = T + 2 * PH + 70 + 40
    legend(img, dr, 110, y, [("nogeom", "no geometry (invalid range)")])
    B.colorbar(img, 110 + 760, y + 2, 520, 18, lo, hi)
    return img


def continuity(d: Data) -> Image.Image:
    rimg, (lo, hi) = range_layer(d)
    rimg = (0.55 * rimg + 0.45 * 255).astype(np.uint8)
    rimg[cut_mask(d) | valid_border(d)] = S.INK
    s = d.summ

    def after(img, dr, L, T):
        B.hatch_cells(img, (L, T), ~d.valid, SC)

    return pano(rimg, "Local range continuity: where the sphere graph is cut",
                [f"seam-aware 8-neighbour graph; retain iff C = |p_i - p_j| / (mean range x true angular step) <= sec 75 deg "
                 f"= {SP.C_MAX:.6f}",
                 f"{s['candidate_pairs']:,} candidate pairs: {s['retained_edges']:,} retained, {s['cut_edges']:,} cut "
                 f"(ink: cut edges and valid / invalid borders)"],
                BADGES["continuity-boundaries.png"], after=after,
                leg=lambda img, dr, x, y: legend(img, dr, x, y, [("cut", "cut continuity edge / validity border"),
                                                                 ("nogeom", "no geometry")]))


def hypotheses(d: Data) -> Image.Image:
    s = d.summ

    def after(img, dr, L, T):
        B.hatch_cells(img, (L, T), ~d.valid, SC)
        dr = ImageDraw.Draw(img)
        for hp in d.hyps[:25]:
            sd = hp["seed"]
            x, y = B.xy(sd["yaw_deg"], sd["pitch_deg"])
            S.text(dr, (L + x, T + y), hp["id"], size=SMALL - 3, bold=True, plate=S.WHITE, anchor="mm")

    return pano(hyp_layer(d), "Natural hypotheses: connected components of range continuity",
                [f"{s['hypotheses']:,} temporary hypotheses ({s['singletons']:,} singletons, {s['multi_cell']:,} with > 1 cell); "
                 f"every component kept; ids by spherical support",
                 "one flat colour per hypothesis, ink at hypothesis changes; no Blender identity, no RGB, no filtering"],
                BADGES["hypothesis-panorama.png"], after=after,
                leg=lambda img, dr, x, y: legend(img, dr, x, y, [("cut", "hypothesis boundary"), ("nogeom", "no geometry")]))


def seeds(d: Data) -> Image.Image:
    tw = 520

    def after(img, dr, L, T):
        B.hatch_cells(img, (L, T), ~d.valid, SC)
        dr = ImageDraw.Draw(img)
        draw_seeds(dr, d, L, T, PW, PH, 1.0, labels=25)
        x0 = L + PW + 60
        S.text(dr, (x0, T - 4), "25 largest hypotheses", size=S.T_SMALL, bold=True, outline=None, anchor="ld")
        S.text(dr, (x0, T + 8), "id        cells        sr      clearance", size=SMALL - 1, fill=S.INK2, outline=None)
        for k, hp in enumerate(d.hyps[:25]):
            c = hp["max_interior_clearance_deg"]
            S.text(dr, (x0, T + 34 + 27 * k), f"{hp['id']}  {hp['cells']:>7,}  {hp['support_sr']:>7.4f}  "
                   f"{'fallback' if c is None else f'{c:6.2f} deg'}", size=SMALL - 1, outline=None)

    return pano(hyp_layer(d, pale=0.62), "Deep-interior seed per hypothesis (DERIVED; no observation)",
                ["seed = the hypothesis cell farthest from its boundary (multi-source Dijkstra along retained edges, "
                 "true angular cost); ties within 1e-12 rad -> smaller row, column",
                 "diamond size grows with interior clearance; singletons are small dots; labels: the 25 largest"],
                BADGES["seed-panorama.png"], after=after, extra_right=tw,
                leg=lambda img, dr, x, y: legend(img, dr, x, y, [("seed", "seed (multi-cell)"), ("dot", "singleton seed"),
                                                                 ("cut", "hypothesis boundary"), ("nogeom", "no geometry")]))


def bars(img, d_bins: dict, title_x: str, x0, y0, pw, ph, stacks, labels_fmt, zero_label=None, colors=None) -> None:
    """Stacked bar chart over declared bins; ``stacks`` = list of (counts list, colour, hatched)."""
    dr = ImageDraw.Draw(img)
    nb = len(stacks[0][0])
    tot = [sum(s[0][k] for s in stacks) for k in range(nb)]
    ymax = max(1, max(tot))
    step = 10 ** math.floor(math.log10(ymax)) if ymax >= 10 else 1
    top = math.ceil(ymax / step) * step
    for v in np.arange(0, top + 0.5 * step, step):
        y = y0 + ph - v / top * ph
        dr.line([x0, y, x0 + pw, y], fill=S.GRID)
        S.text(dr, (x0 - 10, y), f"{int(v):,}", size=SMALL, fill=S.INK2, outline=None, anchor="rm")
    bw = pw / nb
    for k in range(nb):
        bx0, bx1 = x0 + k * bw + 3, x0 + (k + 1) * bw - 3
        yb = y0 + ph
        for counts, col, hat in stacks:
            n = counts[k]
            if n:
                yt = min(yb - n / top * ph, yb - 4)   # a non-zero count stays visible
                dr.rounded_rectangle([bx0, yt, bx1, yb - 2], radius=1, fill=col)
                if hat:
                    S.hatch(img, [bx0, yt, bx1, yb - 2], S.WHITE, spacing=7, width=2)
                    dr = ImageDraw.Draw(img)
                yb = yt - 2
        if tot[k]:
            S.text(dr, ((bx0 + bx1) / 2, yb - 4), f"{tot[k]:,}", size=SMALL - 2, bold=True, outline=None, anchor="md")
        lab = labels_fmt(k)
        if lab:
            S.text(dr, ((bx0 + bx1) / 2, y0 + ph + 8), lab, size=SMALL - 3, fill=S.INK2, outline=None, anchor="ma")
    S.text(dr, (x0 + pw / 2, y0 + ph + 40), title_x, size=S.T_SMALL, fill=S.INK2, outline=None, anchor="ma")


def support_hist(d: Data) -> Image.Image:
    img = Image.new("RGB", (1600, 980), S.SURFACE)
    B.header(img, "Hypothesis support: how much of the sphere each range-connected hypothesis covers",
             ["bins declared before discovery (edges 10^(k/2) sr); stacked: multi-cell hypotheses (blue) and singletons "
              "(orange, hatched)", "counts are hypotheses; every component is kept, including singletons"],
             BADGES["hypothesis-support-histogram.png"])
    e = SP.SUPPORT_EDGES_SR
    nb = len(e) - 1
    sing, multi = [0] * nb, [0] * nb
    for h in d.hyps:
        k = min(max(int(np.searchsorted(e, h["support_sr"], side="right") - 1), 0), nb - 1)
        (sing if h["cells"] == 1 else multi)[k] += 1
    bars(img, None, "hypothesis support (steradian, log scale bins)", 200, 200, 1300, 600,
         [(multi, MULTI, False), (sing, SINGLE, True)], lambda k: f"1e{e[k] and int(round(math.log10(e[k])))}" if k % 2 == 0 else "")
    dr = ImageDraw.Draw(img)
    s = d.summ
    y = 900
    dr.rounded_rectangle([200, y, 226, y + 20], radius=3, fill=MULTI)
    S.text(dr, (236, y + 10), f"multi-cell ({s['multi_cell']:,})", size=SMALL, outline=None, anchor="lm")
    dr.rounded_rectangle([520, y, 546, y + 20], radius=3, fill=SINGLE)
    S.hatch(img, [520, y, 546, y + 20], S.WHITE, spacing=7, width=2)
    dr = ImageDraw.Draw(img)
    S.text(dr, (556, y + 10), f"singleton ({s['singletons']:,})", size=SMALL, outline=None, anchor="lm")
    tk = s["top_k_support"]
    S.text(dr, (860, y + 10), "largest K cover: " + "  ".join(f"K={k}: {100 * tk[str(k)]['fraction_of_4pi']:.1f}%"
                                                            for k in SP.TOP_K), size=SMALL, bold=True, outline=None, anchor="lm")
    return img


def clearance_hist(d: Data) -> Image.Image:
    img = Image.new("RGB", (1600, 980), S.SURFACE)
    B.header(img, "Seed interior clearance: how deep inside its hypothesis each seed sits",
             ["angular distance from the seed to the nearest boundary cell along the hypothesis graph; zero counted "
              "separately (singletons and all-boundary hypotheses)",
              "bins declared before discovery (edges 2^(k/2) degrees); stacked: multi-cell (blue) and singletons (orange)"],
             BADGES["interior-clearance-histogram.png"])
    e = SP.CLEARANCE_EDGES_DEG
    nb = len(e) - 1
    sing, multi = [0] * (nb + 1), [0] * (nb + 1)
    for h in d.hyps:
        c = h["max_interior_clearance_deg"]
        if c is None:
            continue
        k = 0 if c == 0 else 1 + min(max(int(np.searchsorted(e, c, side="right") - 1), 0), nb - 1)
        (sing if h["cells"] == 1 else multi)[k] += 1
    bars(img, None, "maximum interior clearance (degrees; first bar = exactly 0)", 200, 200, 1300, 600,
         [(multi, MULTI, False), (sing, SINGLE, True)],
         lambda k: "0" if k == 0 else (f"{e[k - 1]:g}" if (k - 1) % 2 == 0 else ""))
    dr = ImageDraw.Draw(img)
    s = d.summ
    q = s["clearance_quantiles_deg"]
    S.text(dr, (200, 905), f"zero-clearance seeds {s['zero_clearance_seeds']:,}; no-boundary fallbacks "
           f"{s['no_boundary_fallbacks']}; median {q[4]:.3f} deg, 99% {q[7]:.2f} deg, max {q[8]:.2f} deg",
           size=SMALL, bold=True, outline=None)
    return img


def overlap_fig(d: Data) -> Image.Image:
    per_h = {r["id"]: r for r in d.ov["per_hypothesis"]}
    top = [h["id"] for h in d.hyps[:25]]
    cols = []
    for hid in top:
        for f in per_h[hid]["fractions"][:3]:
            if f["o"] not in cols:
                cols.append(f["o"])
    if 0 in cols:
        cols.remove(0)
    cols = cols[:22] + [0]
    cw, rh, x0, y0 = 46, 30, 230, 330
    W = x0 + cw * len(cols) + 380
    img = Image.new("RGB", (max(W, 1240), y0 + rh * len(top) + 90), S.SURFACE)
    B.header(img, "Natural hypotheses versus authored identity",
             ["percent of each natural hypothesis's support in each authored Object Index",
              "(columns; O_0 = valid geometry without a catalog id); rows: the 25 largest hypotheses",
              "descriptive reference comparison: not a ground-truth confusion matrix, no accuracy implied"],
             BADGES["overlap-matrix.png"])
    dr = ImageDraw.Draw(img)
    names = {r["o"]: r["name"] for r in d.ov["per_reference_id"]}
    for j, o in enumerate(cols):
        x = x0 + j * cw + cw / 2
        lab = "O_0" if o == 0 else f"{o} {names.get(o, '')[:12]}"
        tmp = Image.new("RGBA", (220, 24), (0, 0, 0, 0))
        S.text(ImageDraw.Draw(tmp), (2, 12), lab, size=SMALL - 3, fill=S.INK, outline=None, anchor="lm")
        tmp = tmp.rotate(60, expand=True)
        img.paste(tmp, (int(x - 12), y0 - tmp.size[1] - 4), tmp)
    dr = ImageDraw.Draw(img)
    for i, hid in enumerate(top):
        y = y0 + i * rh
        S.text(dr, (x0 - 10, y + rh / 2), f"{hid}  {per_h[hid]['support_sr']:.3f} sr", size=SMALL - 2, outline=None, anchor="rm")
        fr = {f["o"]: f["fraction"] for f in per_h[hid]["fractions"]}
        for j, o in enumerate(cols):
            v = fr.get(o, 0.0)
            col = tuple(int(c) for c in (np.array([250, 250, 248]) * (1 - v) + np.array([133, 94, 20]) * v))
            dr.rectangle([x0 + j * cw + 1, y + 1, x0 + (j + 1) * cw - 1, y + rh - 1], fill=col)
            if o == 0 and v > 0:
                S.hatch(img, [x0 + j * cw + 1, y + 1, x0 + (j + 1) * cw - 1, y + rh - 1], (255, 255, 255), spacing=5, width=1)
                dr = ImageDraw.Draw(img)
            if v >= 0.005:
                S.text(dr, (x0 + j * cw + cw / 2, y + rh / 2), f"{int(round(100 * v))}", size=SMALL - 5,
                       fill=S.WHITE if v > 0.55 else S.INK, outline=None, anchor="mm")
        other = 1.0 - sum(fr.get(o, 0.0) for o in cols)
        S.text(dr, (x0 + len(cols) * cw + 14, y + rh / 2), f"other ids {100 * other:.0f}%  ({per_h[hid]['authored_ids_intersected']} authored ids)",
               size=SMALL - 3, fill=S.INK2, outline=None, anchor="lm")
    a = d.ov["accounting"]
    S.text(dr, (x0, y0 + rh * len(top) + 30), f"cells: catalog {a['catalog_cells']:,} / O_0 {a['O0_cells']:,} (matches Breadth-1: "
           f"{a['matches_breadth1']}); numbers are percent of the row's support", size=SMALL, outline=None)
    return img


def rgb_contrast(d: Data) -> Image.Image:
    img = Image.new("RGB", (110 + PW + 40, 1560), S.SURFACE)
    B.header(img, "RGB diagnostic (post-freeze): colour change across range edges",
             ["contrast = || sRGB-decoded linear rgb_i - rgb_j || over each neighbour pair; no threshold; RGB caused "
              "no merge, split, seed change or deletion",
              "top: distribution per edge class (declared bins, fraction of edges); bottom: strongest colour change on "
              "retained edges inside range hypotheses"], BADGES["rgb-edge-contrast.png"])
    dr = ImageDraw.Draw(img)
    e = SP.RGB_CONTRAST_EDGES
    x0, y0, pw, ph = 200, 190, 1300, 420
    dists = [("retained (inside hypotheses)", d.rgbd["retained"], MULTI), ("cut (range discontinuities)", d.rgbd["cut"], S.OI_VERM)]
    nb = len(e) - 1
    fmax = 0.0
    fr = []
    for name, dd, col in dists:
        n = max(dd["edges_n"], 1)
        f = [dd["binned"]["zero"] / n] + [c / n for c in dd["binned"]["counts"]]
        fr.append(f)
        fmax = max(fmax, max(f))
    dr.rectangle([x0, y0, x0 + pw, y0 + ph], outline=S.INK2)
    bw = pw / (nb + 1)
    for (name, dd, col), f in zip(dists, fr):
        pts = []
        for k, v in enumerate(f):
            y = y0 + ph - v / fmax * ph
            pts += [(x0 + k * bw, y), (x0 + (k + 1) * bw, y)]
        dr.line(pts, fill=col, width=3)
    for k in range(nb + 1):
        if k == 0 or (k - 1) % 4 == 0:
            lab = "0" if k == 0 else f"1e{int(round(math.log10(e[k - 1])))}"
            S.text(dr, (x0 + k * bw + bw / 2, y0 + ph + 8), lab, size=SMALL - 2, fill=S.INK2, outline=None, anchor="ma")
    S.text(dr, (x0 + pw / 2, y0 + ph + 36), "linear-RGB contrast across the edge (log bins; first bin = exactly 0)",
           size=S.T_SMALL, fill=S.INK2, outline=None, anchor="ma")
    for i, (name, dd, col) in enumerate(dists):
        y = y0 + 20 + 28 * i
        dr.line([x0 + 20, y, x0 + 50, y], fill=col, width=3)
        q = dd["quantiles"]
        S.text(dr, (x0 + 60, y), f"{name}: {dd['edges_n']:,} edges, median {q[4]:.4f}, 95% {q[6]:.3f}", size=SMALL,
               outline=None, anchor="lm")
    v = d.intra_max
    vmax = max(float(np.percentile(v[v > 0], 99.5)), 1e-6) if (v > 0).any() else 1.0
    t = np.clip(v / vmax, 0, 1)[..., None]
    m = (np.array([245, 245, 243]) * (1 - t) + np.array([60, 20, 90]) * t).astype(np.uint8)
    m[~d.valid] = B.NO_GEOM
    big = B.up(m)
    big[B.boundary_mask(d.labels.astype(np.int64))] = (150, 150, 150)
    T2 = y0 + ph + 110
    img.paste(Image.fromarray(big), (110, T2))
    B.hatch_cells(img, (110, T2), ~d.valid, SC)
    dr = ImageDraw.Draw(img)
    B.axes(dr, 110, T2, PW, PH)
    S.text(dr, (110, T2 + PH + 40), f"cell value: maximum contrast over its retained edges (light 0 -> dark >= {vmax:.3f}, "
           "the 99.5th percentile); gray lines: hypothesis boundaries", size=SMALL, fill=S.INK2, outline=None)
    return img


def overview(d: Data) -> Image.Image:
    W, H = 3040, 2060
    img = Image.new("RGB", (W, H), S.SURFACE)
    dr = ImageDraw.Draw(img)
    s, a = d.summ, d.ov["accounting"]
    S.text(dr, (40, 28), "Natural Bootstrap-1a · spherical range connectivity", size=S.T_HUGE - 12, bold=True, outline=None)
    S.text(dr, (40, 100), "Can local 3-D range continuity alone turn the broad spherical glance into connected perceptual "
           "hypotheses and seeds, without Blender object identity?", size=S.T_BODY, fill=S.INK2, outline=None)
    S.text(dr, (40, 134), f"One rule: connect neighbouring cells iff C = |p_i - p_j| / (mean range x true angular step) <= "
           f"sec 75 deg.  Range is a controlled sensory proxy (Blender Position), not stereo.  No new observation.",
           size=S.T_BODY, fill=S.INK2, outline=None)
    xr = W - 40
    for b in BADGES["overview.png"]:
        xr = S.badge(img, xr, 34, b) - 10
    regions = [(40, 190), (1560, 190), (40, 1120), (1560, 1120)]
    RW, RH = 1440, 900
    titles = [("A · sensory proxy: RGB and radial range", [ORA]), ("B · local range continuity (cut edges)", [DER]),
              ("C · natural hypotheses and deep-interior seeds", [DER]),
              ("D · reference: relation to authored identity", [REF])]
    for (rx, ry), (t, bs) in zip(regions, titles):
        dr.rounded_rectangle([rx - 10, ry - 10, rx + RW + 10, ry + RH], radius=10, fill=S.PANEL, outline=S.GRID)
        S.text(dr, (rx + 4, ry + 4), t, size=S.T_HEAD, bold=True, outline=None)
        xr = rx + RW
        for b in bs:
            xr = S.badge(img, xr, ry + 4, b) - 10
        dr = ImageDraw.Draw(img)
    oy = 70
    (ax, ay), (bx, by), (cx, cy), (qx, qy) = regions
    # A: RGB and range side by side at 1x, then the proxy statement
    img.paste(Image.fromarray(d.srgb8), (ax, ay + oy))
    r1, (lo, hi) = range_layer(d, 1)
    img.paste(Image.fromarray(r1), (ax + 720, ay + oy))
    B.hatch_cells(img, (ax + 720, ay + oy), ~d.valid, 1)
    dr = ImageDraw.Draw(img)
    for x in (ax, ax + 720):
        dr.rectangle([x - 1, ay + oy - 1, x + 720, ay + oy + 360], outline=S.INK2)
    S.text(dr, (ax, ay + oy + 372), "RGB (diagnostic only)", size=SMALL, fill=S.INK2, outline=None)
    S.text(dr, (ax + 720, ay + oy + 372), "radial range (log; light near, dark far; hatched: no geometry)", size=SMALL,
           fill=S.INK2, outline=None)
    B.colorbar(img, ax + 720, ay + oy + 404, 520, 16, lo, hi)
    dr = ImageDraw.Draw(img)
    lines = ["Controlled sensory proxy from the accepted Breadth-1 render:",
             f"  {s['valid_cells']:,} valid range cells, {s['invalid_cells']:,} without geometry.",
             "Discovery opened only the stripped range file (guarded; 0 violations):",
             "  no RGB, no Object Index, no catalog, no Breadth-1 or controller products."]
    for k, ln in enumerate(lines):
        S.text(dr, (ax, ay + oy + 470 + 34 * k), ln, size=S.T_SMALL, outline=None, bold=(k % 2 == 0))
    # B: continuity
    rimg, _ = range_layer(d)
    rimg = (0.55 * rimg + 0.45 * 255).astype(np.uint8)
    rimg[cut_mask(d) | valid_border(d)] = S.INK
    img.paste(Image.fromarray(rimg), (bx, by + oy))
    B.hatch_cells(img, (bx, by + oy), ~d.valid, SC)
    # C: hypotheses + seeds
    img.paste(Image.fromarray(hyp_layer(d, pale=0.35)), (cx, cy + oy))
    B.hatch_cells(img, (cx, cy + oy), ~d.valid, SC)
    dr = ImageDraw.Draw(img)
    draw_seeds(dr, d, cx, cy + oy, PW, PH, 1.0, labels=10)
    for rx, ry in regions[1:3]:
        B.axes(dr, rx, ry + oy, PW, PH, words=True, ticks=False)
    S.text(dr, (bx, by + oy + PH + 12), f"ink: {s['cut_edges']:,} cut of {s['candidate_pairs']:,} candidate edges, plus validity "
           f"borders; C_MAX = sec 75 deg = {SP.C_MAX:.4f}", size=SMALL, fill=S.INK2, outline=None)
    tk = s["top_k_support"]
    S.text(dr, (cx, cy + oy + PH + 12), f"{s['hypotheses']:,} hypotheses ({s['singletons']:,} singletons); largest covers "
           f"{100 * s['largest_fraction_of_4pi']:.1f}% of the sphere, largest 5 / 25: {100 * tk['5']['fraction_of_4pi']:.1f}% / "
           f"{100 * tk['25']['fraction_of_4pi']:.1f}%; diamonds grow with interior clearance", size=SMALL, fill=S.INK2, outline=None)
    # D: reference (secondary): authored boundaries (brown) and O_0 (tan) under the natural boundaries (ink)
    per_h = {r["id"]: r for r in d.ov["per_hypothesis"]}
    base = np.full((SP.HEIGHT, SP.WIDTH, 3), 246, np.uint8)
    base[d.o0] = (232, 210, 170)
    base[~d.valid] = B.NO_GEOM
    base[B.boundary_mask(np.where(d.valid, d.oid, -1), 1)] = S.REF_BROWN
    base[B.boundary_mask(d.labels.astype(np.int64), 1)] = S.INK
    img.paste(Image.fromarray(base), (qx, qy + oy))
    B.hatch_cells(img, (qx, qy + oy), ~d.valid, 1)
    dr = ImageDraw.Draw(img)
    dr.rectangle([qx - 1, qy + oy - 1, qx + 720, qy + oy + 360], outline=S.INK2)
    S.text(dr, (qx, qy + oy + 372), "ink: natural boundaries; brown: authored Object Index boundaries;",
           size=SMALL - 1, fill=S.INK2, outline=None)
    S.text(dr, (qx, qy + oy + 394), "tan: O_0 (geometry without a catalog id); hatched: no geometry",
           size=SMALL - 1, fill=S.INK2, outline=None)
    bx0, by0 = qx + 760, qy + oy
    S.text(dr, (bx0, by0), "composition of the 12 largest hypotheses", size=S.T_SMALL, bold=True, outline=None)
    S.text(dr, (bx0, by0 + 28), "by authored Object Index (dominant 2 named) and O_0", size=SMALL - 1, fill=S.INK2, outline=None)
    for i, h in enumerate(d.hyps[:12]):
        y = by0 + 64 + 34 * i
        r = per_h[h["id"]]
        S.text(dr, (bx0, y + 11), h["id"], size=SMALL - 2, bold=True, outline=None, anchor="lm")
        x = bx0 + 74
        wtot = 400
        segs = [(f["fraction"], f["o"], f["name"]) for f in r["fractions"]]
        named = [sg for sg in segs if sg[1] != 0][:2]
        o0f = r["O0_fraction"]
        rest = max(0.0, 1.0 - sum(sg[0] for sg in named) - o0f)
        for k, (fv, o, nm) in enumerate(named):
            col = (133, 94, 20) if k == 0 else (190, 155, 95)
            dr.rectangle([x, y, x + fv * wtot, y + 22], fill=col)
            x += fv * wtot
        dr.rectangle([x, y, x + rest * wtot, y + 22], fill=(225, 215, 195))
        x += rest * wtot
        if o0f > 0:
            dr.rectangle([x, y, x + o0f * wtot, y + 22], fill=(250, 240, 222), outline=S.REF_BROWN)
            S.hatch(img, [x, y, x + o0f * wtot, y + 22], (200, 160, 100), spacing=5, width=1)
            dr = ImageDraw.Draw(img)
        parts = [f"{nm[:14]} {100 * fv:.0f}%" for fv, o, nm in named] + ([f"O_0 {100 * o0f:.0f}%"] if o0f > 0.005 else [])
        lab = ", ".join(parts)
        S.text(dr, (bx0 + 74 + wtot + 10, y + 11), lab, size=SMALL - 4, fill=S.INK2, outline=None, anchor="lm")
    ex = d.ov["examples"]
    one = ex["one_natural_to_many_authored"][0]
    many = ex["many_natural_to_one_authored"][0]
    S.text(dr, (qx, qy + oy + 436), "Descriptive relations (reference only; no accuracy implied):", size=S.T_SMALL,
           bold=True, outline=None)
    rel = [f"catalog cells {a['catalog_cells']:,} / O_0 cells {a['O0_cells']:,} (equal to Breadth-1: {a['matches_breadth1']})",
           f"{d.ov['hypotheses_touching_O0']:,} hypotheses touch O_0; {d.ov['authored_ids_touched']} authored ids touched",
           f"one natural -> many authored: {one['id']} spans {one['authored_ids_intersected']} authored ids",
           f"many natural -> one authored: {many['name']} ({many['o']}) meets {many['hypotheses_intersecting']:,} hypotheses"]
    for k, ln in enumerate(rel):
        S.text(dr, (qx, qy + oy + 472 + 30 * k), ln, size=SMALL, outline=None)
    return img


# ------------------------------------------------------------------ entry
def render_all(run: Path):
    d = Data(run)
    return {"overview.png": overview(d), "range-input.png": range_input(d), "continuity-boundaries.png": continuity(d),
            "hypothesis-panorama.png": hypotheses(d), "seed-panorama.png": seeds(d),
            "hypothesis-support-histogram.png": support_hist(d), "interior-clearance-histogram.png": clearance_hist(d),
            "overlap-matrix.png": overlap_fig(d), "rgb-edge-contrast.png": rgb_contrast(d)}, d


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
    from nb1a_run import code_state
    manifest = {"schema": "NB1a-visuals-manifest-v1", "run": str(run), "sources": d.sources, "code": code_state(),
                "regenerate": f".venv/bin/python tools/natural_bootstrap/nb1a_run.py visualize --run {run} --visuals {vis}",
                "products": out,
                "glyphs": {"seed": "ink diamond, larger with interior clearance; singletons small dots",
                           "natural boundary": "thin solid ink", "no geometry": "hatched",
                           "O_0 (reference)": "tan tint / hatched brown", "authored reference": "brown"}}
    (vis / "visuals-manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    print(f"[nb1a] visualize: {len(FIGURES)} figures -> {vis}")
    return manifest
