"""Natural Bootstrap-1b: the persistent human-facing figures.

Contract: docs/natural-bootstrap/nb1b-foveal-serviceability-contract.md, section 13.  Reads only the saved
selection and evaluation outputs, plus (post-freeze) the frozen NB1a label raster and RGB proxy.  Draws
with the accepted Visual Language 1 style and the accepted Breadth-1 panorama helpers, both read-only.  The
natural hypotheses and the sensor fit are the subject; authored identity is the (secondary) reference.
Glyphs:
- ink diamond: NB1a seed;
- solid ring: FULL footprint boundary (R_FULL disk); thin dotted ring: CENTER footprint (R_CENTER disk);
- square outline: the nominal 12-degree core (tangent-plane views);
- class fill plus a non-colour cue: stipple (environment), solid ring (primary), dotted ring (secondary),
  hollow diamond (marginal), dot (edge-only);
- hatched: no geometry.
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
import nb1a_spec as A  # noqa: E402
import nb1b_spec as SP  # noqa: E402
import style as S  # noqa: E402  (Visual Language 1, read-only)

ORA, DER, REF = SP.TRUTH_ORACLE, SP.TRUTH_DERIVED, SP.TRUTH_REFERENCE
SC = 2
PW, PH = A.WIDTH * SC, A.HEIGHT * SC
SMALL = 16
ENV_FILL = (222, 228, 236)
CLASS_STYLE = {   # colour + the non-colour cue (Visual Language 1: every role has both)
    SP.ENVIRONMENT: {"color": S.SLATE, "short": "environment", "cue": "stipple"},
    SP.PRIMARY: {"color": S.OI_GREEN, "short": "primary", "cue": "solid FULL ring"},
    SP.SECONDARY: {"color": S.OI_SKY, "short": "secondary", "cue": "dotted CENTER ring"},
    SP.MARGINAL: {"color": S.OI_ORANGE, "short": "marginal", "cue": "hollow diamond"},
    SP.EDGE_ONLY: {"color": S.OI_PURPLE, "short": "edge-only", "cue": "dot"},
}
FIGURES = ["overview.png", "serviceability-panorama.png", "primary-look-panorama.png", "secondary-look-panorama.png",
           "environment-candidate.png", "footprint-examples.png", "class-counts.png"]
BADGES = {
    "overview.png": [DER, ORA, REF], "serviceability-panorama.png": [DER], "primary-look-panorama.png": [DER, ORA],
    "secondary-look-panorama.png": [DER, ORA], "environment-candidate.png": [DER, REF],
    "footprint-examples.png": [DER], "class-counts.png": [DER],
}
GN_HALF_DEG = 12.0     # half-field of the tangent-plane (gnomonic) views


def sha256(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class Data:
    SOURCES = ["selection/serviceability.json", "selection/footprints.npz", "selection/selection-summary.json",
               "evaluation/candidate-reference-summary.json"]
    NB1A = ["discovery/hypothesis-raster.npz", "input/rgb-sensory.npz"]

    def __init__(self, run: Path):
        self.run = run
        self.recs = json.loads((run / "selection/serviceability.json").read_text())["hypotheses"]
        self.by_id = {r["id"]: r for r in self.recs}
        self.summ = json.loads((run / "selection/selection-summary.json").read_text())
        self.ref = json.loads((run / "evaluation/candidate-reference-summary.json").read_text())
        with np.load(run / "selection/footprints.npz") as z:
            self.fp = {k: z[k] for k in z.files}
        with np.load(SP.NB1A_RUN / "discovery/hypothesis-raster.npz") as z:   # frozen NB1a labels
            self.labels = np.asarray(z["labels"], np.int64)
        with np.load(SP.NB1A_RUN / "input/rgb-sensory.npz") as z:             # RGB proxy, post-freeze only
            self.srgb8 = z["srgb8"]
        self.valid = self.labels > 0
        lut = np.zeros(len(self.recs) + 1, np.int64)
        for r in self.recs:
            lut[r["label"]] = SP.CLASSES.index(r["class"]) + 1
        self.cls = lut[self.labels]                      # 0 = no geometry, else 1 + class index
        self.queue = {n: [self.by_id[e["id"]] for e in self.summ["queues"][n]] for n in ("primary", "secondary")}
        self.env = [r for r in self.recs if r["class"] == SP.ENVIRONMENT]
        self.cand_ref = {c["id"]: c for c in self.ref["candidates"]}
        self.sources = {n: sha256(run / n) for n in self.SOURCES}
        self.sources.update({str(SP.NB1A_RUN / n): sha256(SP.NB1A_RUN / n) for n in self.NB1A})

    def footprint(self, rid: str, kind: str) -> np.ndarray:
        k = self.by_id[rid]["label"] - 1
        p = self.fp[f"{kind}_ptr"]
        return self.fp[f"{kind}_cells"][p[k]:p[k + 1]].astype(np.int64)


# ------------------------------------------------------------------ layers and glyphs
def class_layer(d: Data, s: int = SC, emphasize: str | None = None) -> np.ndarray:
    """Every hypothesis filled by its class; with ``emphasize``, the other classes are faded."""
    col = np.full(d.labels.shape + (3,), 255.0)
    for k, c in enumerate(SP.CLASSES, start=1):
        rgb = np.array(ENV_FILL if c == SP.ENVIRONMENT else CLASS_STYLE[c]["color"], np.float64)
        if emphasize is not None and c != emphasize:
            rgb = 0.22 * rgb + 0.78 * 255
        col[d.cls == k] = rgb
    col[~d.valid] = B.NO_GEOM
    img = B.up(col.astype(np.uint8), s)
    img[B.boundary_mask(d.labels, s)] = S.INK2 if emphasize is None else (150, 150, 150)
    return img


def stipple_cells(img: Image.Image, origin, mask_cells: np.ndarray, s: int, color=(120, 136, 158), spacing=9) -> None:
    """A dot pattern clipped to the masked cells (the environment candidate's non-colour cue)."""
    if not mask_cells.any():
        return
    m = B.up(mask_cells, s)
    layer = np.zeros(m.shape + (4,), np.uint8)
    yy, xx = np.mgrid[0:m.shape[0], 0:m.shape[1]]
    dots = ((yy % spacing) == 0) & (((xx + (yy // spacing % 2) * (spacing // 2)) % spacing) == 0)
    on = dots & m
    layer[on] = color + (255,)
    lay = Image.fromarray(layer, "RGBA")
    img.paste(lay, origin, lay)


def circle_yaw_pitch(d_s, radius: float, n: int = 240) -> tuple[np.ndarray, np.ndarray]:
    d_s = np.asarray(d_s, np.float64)
    a = np.array([0.0, 1.0, 0.0]) if abs(d_s[1]) < 0.9 else np.array([1.0, 0.0, 0.0])
    e1 = np.cross(d_s, a); e1 /= np.linalg.norm(e1)
    e2 = np.cross(d_s, e1)
    t = np.linspace(0.0, 2 * math.pi, n + 1)
    p = math.cos(radius) * d_s[None] + math.sin(radius) * (np.cos(t)[:, None] * e1 + np.sin(t)[:, None] * e2)
    return np.degrees(np.arctan2(p[:, 0], -p[:, 2])), np.degrees(np.arcsin(np.clip(p[:, 1], -1, 1)))


def ring(dr, d_s, radius, ox, oy, w=PW, h=PH, dotted=False, color=S.INK, width=2) -> None:
    """A spherical disk boundary projected to the panorama, split at the longitude seam."""
    yaw, pitch = circle_yaw_pitch(d_s, radius)
    pts = [(ox + (y + 180) / 360 * w, oy + (90 - p) / 180 * h) for y, p in zip(yaw.tolist(), pitch.tolist())]
    runs, cur = [], [pts[0]]
    for a, b in zip(pts[:-1], pts[1:]):
        if abs(b[0] - a[0]) > w / 2:
            runs.append(cur); cur = [b]
        else:
            cur.append(b)
    runs.append(cur)
    for run in runs:
        if len(run) < 2:
            continue
        if dotted:
            S.dashed_line(dr, run, S.WHITE, width=width + 2, dash=3, gap=4)
            S.dashed_line(dr, run, color, width=width, dash=3, gap=4)
        else:
            dr.line(run, fill=S.WHITE, width=width + 3)
            dr.line(run, fill=color, width=width)


def hollow_diamond(dr, x, y, r=5) -> None:
    pts = [(x, y - r), (x + r, y), (x, y + r), (x - r, y), (x, y - r)]
    dr.line(pts, fill=S.WHITE, width=4)
    dr.line(pts, fill=S.INK, width=2)


def seed_glyph(dr, r: dict, ox: int, oy: int, w: int = PW, h: int = PH, rings: bool = True, label: str = "") -> None:
    s = r["seed"]
    x, y = B.xy(s["yaw_deg"], s["pitch_deg"], w, h)
    x, y = ox + x, oy + y
    c = r["class"]
    if c in (SP.PRIMARY, SP.SECONDARY, SP.ENVIRONMENT) and rings:
        if c in (SP.PRIMARY, SP.ENVIRONMENT):
            ring(dr, r["seed_direction_h"], SP.R_FULL_RAD, ox, oy, w, h)
        ring(dr, r["seed_direction_h"], SP.R_CENTER_RAD, ox, oy, w, h, dotted=True)
    if c == SP.MARGINAL:
        hollow_diamond(dr, x, y, 5)
    elif c == SP.EDGE_ONLY:
        dr.rectangle([x - 1.2, y - 1.2, x + 1.2, y + 1.2], fill=S.INK)
    else:
        B.diamond(dr, x, y, 6 if c != SP.ENVIRONMENT else 8)
    if label:
        S.text(dr, (x, y - 26 if s["pitch_deg"] < 80 else y + 26), label, size=SMALL - 1, bold=True, plate=S.WHITE,
               anchor="mm")


def legend(img, dr, x, y, items) -> None:
    for kind, label in items:
        if kind in CLASS_STYLE:
            col = ENV_FILL if kind == SP.ENVIRONMENT else CLASS_STYLE[kind]["color"]
            dr.rectangle([x, y + 1, x + 26, y + 21], fill=col, outline=S.INK2)
            if kind == SP.ENVIRONMENT:
                stipple_cells(img, (x + 1, y + 2), np.ones((10, 13), bool), 2, spacing=6)
                dr = ImageDraw.Draw(img)
        elif kind == "full":
            dr.ellipse([x + 2, y, x + 24, y + 22], outline=S.INK, width=2)
        elif kind == "center":
            S.dashed_ellipse(dr, [x + 5, y + 3, x + 21, y + 19], S.INK, width=2, n=8)
        elif kind == "seed":
            B.diamond(dr, x + 13, y + 11, 6)
        elif kind == "hollow":
            hollow_diamond(dr, x + 13, y + 11, 6)
        elif kind == "dot":
            dr.rectangle([x + 12, y + 10, x + 14, y + 12], fill=S.INK)
        elif kind == "nogeom":
            dr.rectangle([x, y + 1, x + 26, y + 21], fill=B.NO_GEOM, outline=S.MUTED)
            S.hatch(img, [x, y + 1, x + 26, y + 21], S.STIPPLE, spacing=6, width=1)
            dr = ImageDraw.Draw(img)
        elif kind == "square":
            dr.rectangle([x + 3, y + 1, x + 23, y + 21], outline=S.INK, width=2)
        bb = S.text(dr, (x + 36, y + 11), label, size=SMALL, outline=None, anchor="lm")
        x = bb[2] + 28


CLASS_LEGEND = [(SP.ENVIRONMENT, "environment (stipple)"), (SP.PRIMARY, "primary look"), (SP.SECONDARY, "secondary look"),
                (SP.MARGINAL, "marginal"), (SP.EDGE_ONLY, "edge-only"), ("nogeom", "no geometry")]
GLYPH_LEGEND = [("seed", "seed"), ("full", f"FULL disk {SP.R_FULL_DEG:.2f}°"), ("center", f"CENTER disk {SP.R_CENTER_DEG:g}°"),
                ("hollow", "marginal seed"), ("dot", "edge-only seed")]


# ------------------------------------------------------------------ tangent-plane (gnomonic) views
def tangent_basis(d_s) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    f = np.asarray(d_s, np.float64)
    hint = np.array([0.0, 1.0, 0.0]) if abs(f[1]) < 0.98 else np.array([0.0, 0.0, -1.0])
    right = np.cross(f, hint); right /= np.linalg.norm(right)
    return f, right, np.cross(right, f)


def gnomonic_cells(d_s, npx: int, half_deg: float = GN_HALF_DEG) -> np.ndarray:
    """Flat NB1a cell index sampled (nearest cell) at each pixel of an npx x npx tangent-plane view."""
    f, right, up = tangent_basis(d_s)
    t = math.tan(math.radians(half_deg))
    u = (np.arange(npx) + 0.5) / npx * 2 * t - t
    uu, vv = np.meshgrid(u, -u)
    ray = f[None, None] + uu[..., None] * right + vv[..., None] * up
    ray /= np.linalg.norm(ray, axis=-1, keepdims=True)
    yaw = np.degrees(np.arctan2(ray[..., 0], -ray[..., 2]))
    pitch = np.degrees(np.arcsin(np.clip(ray[..., 1], -1, 1)))
    col = np.floor((yaw + 180.0) / A.CELL_DEG).astype(np.int64) % A.WIDTH
    row = np.clip(np.floor((90.0 - pitch) / A.CELL_DEG).astype(np.int64), 0, A.HEIGHT - 1)
    return row * A.WIDTH + col


def core_overlay(dr, ox, oy, npx, half_deg: float = GN_HALF_DEG, color=S.INK) -> None:
    """The nominal square core and the two disks, exactly, in the tangent plane."""
    k = npx / (2 * math.tan(math.radians(half_deg)))
    cx, cy = ox + npx / 2, oy + npx / 2
    a = math.tan(SP.R_CENTER_RAD) * k
    rf = math.tan(SP.R_FULL_RAD) * k
    for col, w in ((S.WHITE, 5), (color, 2)):
        dr.rectangle([cx - a, cy - a, cx + a, cy + a], outline=col, width=w)
        dr.ellipse([cx - rf, cy - rf, cx + rf, cy + rf], outline=col, width=w)
    S.dashed_ellipse(dr, [cx - a, cy - a, cx + a, cy + a], S.WHITE, width=5, n=24)
    S.dashed_ellipse(dr, [cx - a, cy - a, cx + a, cy + a], color, width=2, n=24)
    B.diamond(dr, cx, cy, 5)


def support_tile(d: Data, r: dict, npx: int) -> Image.Image:
    """DERIVED: own hypothesis (class colour), other hypotheses (light), no geometry (hatched)."""
    cells = gnomonic_cells(r["seed_direction_h"], npx)
    lab = d.labels.reshape(-1)[cells]
    img = np.full((npx, npx, 3), 236, np.uint8)
    own = lab == r["label"]
    img[own] = CLASS_STYLE[r["class"]]["color"] if r["class"] != SP.ENVIRONMENT else ENV_FILL
    img[lab == 0] = B.NO_GEOM
    edge = np.zeros(lab.shape, bool)
    edge[:, 1:] |= lab[:, 1:] != lab[:, :-1]
    edge[1:, :] |= lab[1:, :] != lab[:-1, :]
    img[edge] = S.INK2
    out = Image.fromarray(img)
    nog = Image.fromarray(((lab == 0) * 255).astype(np.uint8))
    S.hatch(out, [0, 0, npx, npx], S.STIPPLE, spacing=7, width=1, mask=nog)
    if r["class"] == SP.ENVIRONMENT:
        stipple_cells(out, (0, 0), own, 1, spacing=8)
    return out


def rgb_tile(d: Data, r: dict, npx: int) -> Image.Image:
    """ORACLE INPUT (post-freeze): the RGB proxy around the seed, with the hypothesis outline (DERIVED)."""
    cells = gnomonic_cells(r["seed_direction_h"], npx)
    img = d.srgb8.reshape(-1, 3)[cells].copy()
    lab = d.labels.reshape(-1)[cells] == r["label"]
    edge = np.zeros(lab.shape, bool)
    edge[:, 1:] |= lab[:, 1:] != lab[:, :-1]
    edge[1:, :] |= lab[1:, :] != lab[:-1, :]
    img[edge] = (255, 255, 255)
    return Image.fromarray(img)


def tile_caption(r: dict) -> list[str]:
    """Two short lines: id, class and clearance; CENTER / FULL own cells over sampled cells (✓ SAFE, ✗ not)."""
    c, u = r["center"], r["full"]
    clr = "—" if r["clearance_deg"] is None else f"{r['clearance_deg']:.2f}°"
    return [f"{r['id']} · {CLASS_STYLE[r['class']]['short']} · clearance {clr}",
            f"CENTER {c['own_cells']}/{c['total_cells']} {'✓' if c['safe'] else '✗'} · "
            f"FULL {u['own_cells']}/{u['total_cells']} {'✓' if u['safe'] else '✗'}"]


def geometry_schematic(img: Image.Image, x: int, y: int, size: int) -> None:
    """SENSOR GEOMETRY: the 12-degree square core, its inscribed (6°) and circumscribed (R_FULL) disks, and a
    rolled square still inside R_FULL (tangent-plane scale)."""
    dr = ImageDraw.Draw(img)
    k = size / (2 * math.tan(math.radians(10.5)))
    cx, cy = x + size / 2, y + size / 2
    a = math.tan(SP.R_CENTER_RAD) * k
    rf = math.tan(SP.R_FULL_RAD) * k
    dr.rectangle([x, y, x + size, y + size], fill=S.PANEL, outline=S.GRID)
    dr.ellipse([cx - rf, cy - rf, cx + rf, cy + rf], outline=S.INK, width=3)
    S.dashed_ellipse(dr, [cx - a, cy - a, cx + a, cy + a], S.INK, width=3, n=28)
    dr.rectangle([cx - a, cy - a, cx + a, cy + a], outline=S.OI_GREEN, width=3)
    th = math.radians(30)
    sq = [(cx + a * (math.cos(th) * sx - math.sin(th) * sy), cy + a * (math.sin(th) * sx + math.cos(th) * sy))
          for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1), (-1, -1))]
    S.dashed_line(dr, sq, S.MUTED, width=2, dash=8, gap=6)
    dr.line([cx, cy, cx + a, cy + a], fill=S.INK2, width=2)
    dr.line([cx, cy, cx + a, cy], fill=S.INK2, width=2)
    B.diamond(dr, cx, cy, 5)
    S.text(dr, (cx + a / 2, cy - 4), "6°", size=SMALL, bold=True, outline=S.WHITE, anchor="md")
    S.text(dr, (cx + a * 0.62, cy + a * 0.62 + 6), f"{SP.R_FULL_DEG:.2f}°", size=SMALL, bold=True, outline=S.WHITE,
           anchor="la")
    S.text(dr, (x + 10, y + 10), "tangent plane at the seed", size=SMALL - 2, fill=S.INK2, outline=None)
    S.text(dr, (x + 10, y + size - 30), f"square: nominal {SP.CORE_FOV_DEG:g}° core; dashed: rolled 30°",
           size=SMALL - 3, fill=S.INK2, outline=None)


# ------------------------------------------------------------------ figures
def pano(content, title, lines, badges, after=None, leg=None, extra_bottom: int = 0) -> Image.Image:
    img = B.pano_figure(content, title, lines, badges, legend=leg, after=after)
    if extra_bottom:
        big = Image.new("RGB", (img.size[0], img.size[1] + extra_bottom), S.SURFACE)
        big.paste(img, (0, 0))
        img = big
    return img


def serviceability_panorama(d: Data) -> Image.Image:
    n = d.summ["counts"]

    def after(img, dr, L, T):
        B.hatch_cells(img, (L, T), ~d.valid, SC)
        stipple_cells(img, (L, T), d.cls == SP.CLASSES.index(SP.ENVIRONMENT) + 1, SC)
        dr = ImageDraw.Draw(img)
        for r in reversed(d.recs):
            seed_glyph(dr, r, L, T)
        for name, tag in (("primary", "P"), ("secondary", "S")):
            for r in d.queue[name][:12]:
                seed_glyph(dr, r, L, T, rings=False, label=f"{tag}{r['queue']['rank']}")

    def leg(img, dr, x, y):
        legend(img, dr, x, y, CLASS_LEGEND)
        legend(img, ImageDraw.Draw(img), x, y + 30, GLYPH_LEGEND)

    return pano(class_layer(d), "Foveal serviceability of every NB1a hypothesis at its unchanged seed",
                [f"{len(d.recs)} hypotheses: environment {n[SP.ENVIRONMENT]}, primary {n[SP.PRIMARY]}, secondary "
                 f"{n[SP.SECONDARY]}, marginal {n[SP.MARGINAL]}, edge-only {n[SP.EDGE_ONLY]}",
                 f"primary: FULL disk ({SP.R_FULL_DEG:.2f}°, circumscribing the {SP.CORE_FOV_DEG:g}° square core) inside the "
                 f"hypothesis; secondary: only the CENTER disk ({SP.R_CENTER_DEG:g}°); no observation, not objectness"],
                BADGES["serviceability-panorama.png"], after=after, leg=leg, extra_bottom=40)


def tiles_grid(img, d: Data, recs: list[dict], x0: int, y0: int, per_row: int, npx: int, kind: str) -> None:
    dr = ImageDraw.Draw(img)
    for k, r in enumerate(recs):
        x = x0 + (k % per_row) * (npx + 90)
        y = y0 + (k // per_row) * (npx + 96)
        tile = rgb_tile(d, r, npx) if kind == "rgb" else support_tile(d, r, npx)
        img.paste(tile, (x, y))
        dr = ImageDraw.Draw(img)
        core_overlay(dr, x, y, npx)
        dr.rectangle([x - 1, y - 1, x + npx, y + npx], outline=S.INK2)
        q = r["queue"]
        if q:
            S.text(dr, (x + 6, y + 6), f"{q['name'][0].upper()}{q['rank']}", size=SMALL - 1, bold=True, plate=S.WHITE)
        cap = tile_caption(r)
        S.text(dr, (x, y + npx + 8), cap[0], size=SMALL - 4, bold=True, outline=None)
        S.text(dr, (x, y + npx + 30), cap[1], size=SMALL - 4, fill=S.INK2, outline=None)
        ref = d.cand_ref.get(r["id"])
        if ref is not None and kind == "rgb":
            S.text(dr, (x, y + npx + 52), f"ref: O_0 {100 * ref['O0_fraction']:.0f}%, {ref['authored_ids_intersected']} authored "
                   "ids", size=SMALL - 4, fill=S.REF_BROWN, outline=None)


def look_panorama(d: Data, name: str) -> Image.Image:
    cls = SP.PRIMARY if name == "primary" else SP.SECONDARY
    q = d.queue[name]
    npx, per_row = 200, 5
    rows = max(1, math.ceil(len(q) / per_row))
    extra = 90 + rows * (npx + 96)
    tag = name[0].upper()

    def after(img, dr, L, T):
        B.hatch_cells(img, (L, T), ~d.valid, SC)
        stipple_cells(img, (L, T), d.cls == SP.CLASSES.index(SP.ENVIRONMENT) + 1, SC)
        dr = ImageDraw.Draw(img)
        for r in q:
            ring(dr, r["seed_direction_h"], SP.R_FULL_RAD, L, T)
            ring(dr, r["seed_direction_h"], SP.R_CENTER_RAD, L, T, dotted=True)
            seed_glyph(dr, r, L, T, rings=False, label=f"{tag}{r['queue']['rank']}")

    rule = (f"FULL disk ({SP.R_FULL_DEG:.2f}°) entirely inside the hypothesis: the whole nominal {SP.CORE_FOV_DEG:g}° square "
            "core fits at any roll") if cls == SP.PRIMARY else \
        (f"CENTER disk ({SP.R_CENTER_DEG:g}°) inside, FULL disk not: the square corners may cross the boundary")
    img = pano(class_layer(d, emphasize=cls),
               (f"Primary look queue: {len(q)} robust sensor-qualified candidates" if cls == SP.PRIMARY else
                f"Secondary look queue: {len(q)} candidates with peripheral-boundary risk"),
               [rule, f"queue order: NB1a seed clearance desc, support desc, id; labels {tag}1…; rings: FULL solid, CENTER "
                "dotted; no entry causes an observation"],
               BADGES[f"{name}-look-panorama.png"], after=after,
               leg=lambda img, dr, x, y: legend(img, dr, x, y, [(cls, CLASS_STYLE[cls]["short"]), ("seed", "seed"),
                                                                ("full", "FULL disk"), ("center", "CENTER disk"),
                                                                ("nogeom", "no geometry")]),
               extra_bottom=extra)
    dr = ImageDraw.Draw(img)
    y0 = img.size[1] - extra + 20
    S.text(dr, (110, y0), "RGB proxy around each seed (tangent plane ±12°, post-freeze, appearance only): square = "
           f"{SP.CORE_FOV_DEG:g}° core, dotted = CENTER, solid = FULL; white = hypothesis outline",
           size=SMALL, fill=S.INK2, outline=None)
    if not q:
        S.text(dr, (110, y0 + 50), f"no {cls} candidate", size=S.T_BODY, bold=True, outline=None)
    tiles_grid(img, d, q, 110, y0 + 40, per_row, npx, "rgb")
    return img


def environment_figure(d: Data) -> Image.Image:
    env = d.env

    def after(img, dr, L, T):
        B.hatch_cells(img, (L, T), ~d.valid, SC)
        stipple_cells(img, (L, T), d.cls == SP.CLASSES.index(SP.ENVIRONMENT) + 1, SC)
        dr = ImageDraw.Draw(img)
        for r in env:
            seed_glyph(dr, r, L, T, label=r["id"])

    lines = [f"rule declared before evaluation: support > 2π sr (more than one hemisphere); geometric, not semantic "
             f"background; not queued, not deleted"]
    if env:
        r = env[0]
        lines.append(f"{r['id']}: {r['support_sr']:.4f} sr = {100 * r['fraction_of_4pi']:.1f}% of the sphere; seed clearance "
                     f"{r['clearance_deg']:.2f}°; CENTER {r['center']['own_cells']}/{r['center']['total_cells']}, FULL "
                     f"{r['full']['own_cells']}/{r['full']['total_cells']} own cells")
    else:
        lines.append("no hypothesis exceeds 2π sr")
    img = pano(class_layer(d, emphasize=SP.ENVIRONMENT), "Environment candidate: the connected scene shell", lines,
               BADGES["environment-candidate.png"], after=after,
               leg=lambda img, dr, x, y: legend(img, dr, x, y, [(SP.ENVIRONMENT, "environment candidate"), ("seed", "seed"),
                                                                ("full", "FULL disk"), ("center", "CENTER disk"),
                                                                ("nogeom", "no geometry")]),
               extra_bottom=170)
    dr = ImageDraw.Draw(img)
    y0 = img.size[1] - 160
    for e in d.ref["environment"]:
        bx = 110
        dr.rectangle([bx - 10, y0 - 8, bx + PW, y0 + 132], outline=S.REF_BROWN, width=2)
        S.badge(img, bx + PW - 6, y0, REF)
        dr = ImageDraw.Draw(img)
        S.text(dr, (bx, y0), "Reference (post-freeze, descriptive only; no effect on the class)", size=S.T_SMALL, bold=True,
               outline=None)
        S.text(dr, (bx, y0 + 34), f"{e['id']} intersects {e['authored_ids_intersected']} authored ids; O_0 (noncatalog) "
               f"{100 * e['O0_fraction']:.1f}%, catalog {100 * e['catalog_fraction']:.1f}% of its support", size=SMALL,
               outline=None)
        top = ", ".join(f"{c['name']} {100 * c['fraction']:.1f}%" for c in e["composition"][:6])
        S.text(dr, (bx, y0 + 62), f"largest reference ids: {top}", size=SMALL, outline=None)
        fr = e["full_footprint_reference"]
        ids = ", ".join(f"{c['name']} {c['cells']}" for c in fr["ids"][:3])
        S.text(dr, (bx, y0 + 90), f"inside its FULL footprint ({fr['cells']} cells): {ids}", size=SMALL, outline=None)
    return img


def example_set(d: Data) -> list[dict]:
    """Examples chosen by rank only: queue heads, the deepest marginal, the largest edge-only, the environment."""
    out = []
    for name in ("primary", "secondary"):
        if d.queue[name]:
            out.append(d.queue[name][0])
    if len(d.queue["primary"]) > 1:
        out.append(d.queue["primary"][-1])
    marg = sorted([r for r in d.recs if r["class"] == SP.MARGINAL], key=lambda r: (-r["clearance_rad"], -r["support_sr"], r["id"]))
    edge = sorted([r for r in d.recs if r["class"] == SP.EDGE_ONLY], key=lambda r: (-r["support_sr"], r["id"]))
    out += marg[:1] + edge[:1] + d.env[:1]
    return out


def footprint_examples(d: Data) -> Image.Image:
    ex = example_set(d)
    npx, gap = 300, 50
    W = 110 + max(4, len(ex)) * (npx + gap)
    img = Image.new("RGB", (max(W, 1900), 1060), S.SURFACE)
    B.header(img, "Footprint test in the tangent plane at each unchanged NB1a seed",
             [f"square: nominal {SP.CORE_FOV_DEG:g}° measurement core (tools/fsg_geometry.py); dotted: CENTER disk "
              f"{SP.R_CENTER_DEG:g}° (inscribed); solid: FULL disk atan(√2·tan 6°) = {SP.R_FULL_DEG:.3f}° (circumscribed)",
              "SAFE = every sampled 0.5° cell in the disk has range and belongs to the hypothesis; examples chosen by rank "
              "(queue heads, deepest marginal, largest edge-only, environment)"], BADGES["footprint-examples.png"])
    geometry_schematic(img, 110, 160, 340)
    dr = ImageDraw.Draw(img)
    notes = ["Why two disks:",
             "• the CENTER disk is the largest disk inside the square core for every roll;",
             "• the FULL disk contains the square core for every roll;",
             "• FULL safe → PRIMARY; only CENTER safe → SECONDARY.",
             "Cells are sampled at 0.5°; a cell exactly at the radius is inside.",
             "This is support containment of the nominal core,",
             "not stereo success, visibility or objectness."]
    for k, ln in enumerate(notes):
        S.text(dr, (490, 175 + 34 * k), ln, size=S.T_SMALL, bold=(k == 0), outline=None)
    legend(img, dr, 490, 175 + 34 * len(notes) + 16, [(SP.PRIMARY, "own hypothesis (class colour)"),
                                                      ("nogeom", "no geometry"), ("square", "core")])
    y0 = 600
    for k, r in enumerate(ex):
        x = 110 + k * (npx + gap)
        img.paste(support_tile(d, r, npx), (x, y0))
        dr = ImageDraw.Draw(img)
        core_overlay(dr, x, y0, npx)
        dr.rectangle([x - 1, y0 - 1, x + npx, y0 + npx], outline=S.INK2)
        cap = tile_caption(r)
        q = r["queue"]
        S.text(dr, (x, y0 - 34), (f"{q['name']} queue #{q['rank']}" if q else CLASS_STYLE[r["class"]]["short"]),
               size=SMALL, bold=True, outline=None)
        S.text(dr, (x, y0 + npx + 10), cap[0], size=SMALL - 3, bold=True, outline=None)
        S.text(dr, (x, y0 + npx + 32), cap[1], size=SMALL - 4, fill=S.INK2, outline=None)
    return img


def class_counts(d: Data) -> Image.Image:
    img = Image.new("RGB", (1800, 1000), S.SURFACE)
    B.header(img, "Serviceability classes: counts and NB1a seed clearance",
             ["left: hypotheses per class (every accepted NB1a hypothesis exactly once); right: seed interior clearance per "
              "hypothesis, log scale, with the two footprint radii for orientation",
              "classes come from exact footprint containment, not from clearance (clearance is the graph distance to the "
              "nearest boundary cell)"], BADGES["class-counts.png"])
    dr = ImageDraw.Draw(img)
    n = d.summ["counts"]
    x0, y0, bw, gap, ph = 140, 220, 90, 40, 560
    top = max(1, max(n.values()))
    for k, c in enumerate(SP.CLASSES):
        x = x0 + k * (bw + gap)
        h = max(4, n[c] / top * ph) if n[c] else 0
        col = ENV_FILL if c == SP.ENVIRONMENT else CLASS_STYLE[c]["color"]
        if h:
            dr.rectangle([x, y0 + ph - h, x + bw, y0 + ph], fill=col, outline=S.INK2)
            if c == SP.ENVIRONMENT:
                m = np.zeros((int(h) // 2 + 1, bw // 2), bool); m[:] = True
                stipple_cells(img, (x + 1, int(y0 + ph - h) + 1), m[: max(1, int(h) // 2 - 1)], 2, spacing=7)
                dr = ImageDraw.Draw(img)
        S.text(dr, (x + bw / 2, y0 + ph - h - 8), f"{n[c]}", size=S.T_SMALL, bold=True, outline=None, anchor="md")
        S.text(dr, (x + bw / 2, y0 + ph + 12), CLASS_STYLE[c]["short"], size=SMALL - 1, outline=None, anchor="ma")
        S.text(dr, (x + bw / 2, y0 + ph + 36), CLASS_STYLE[c]["cue"], size=SMALL - 5, fill=S.INK2, outline=None, anchor="ma")
    dr.line([x0 - 10, y0 + ph, x0 + 5 * (bw + gap), y0 + ph], fill=S.INK2)
    S.text(dr, (x0, y0 + ph + 80), f"total {len(d.recs)} = accepted NB1a hypotheses", size=S.T_SMALL, bold=True, outline=None)
    # right: clearance strip
    lx0, lw = 880, 820
    lo, hi = math.log10(0.2), math.log10(100.0)

    def px(v):
        return lx0 + (math.log10(v) - lo) / (hi - lo) * lw
    rows = [c for c in SP.CLASSES]
    for v in (0.25, 0.5, 1, 2, 4, 8, 16, 32, 64):
        x = px(v)
        dr.line([x, y0, x, y0 + ph], fill=S.GRID)
        S.text(dr, (x, y0 + ph + 10), f"{v:g}°", size=SMALL - 2, fill=S.INK2, outline=None, anchor="ma")
    for v, lab, dotted in ((SP.R_CENTER_DEG, "R_CENTER 6°", True), (SP.R_FULL_DEG, f"R_FULL {SP.R_FULL_DEG:.2f}°", False)):
        x = px(v)
        if dotted:
            S.dashed_line(dr, [(x, y0 - 10), (x, y0 + ph)], S.INK, width=2, dash=4, gap=4)
        else:
            dr.line([x, y0 - 10, x, y0 + ph], fill=S.INK, width=2)
        S.text(dr, (x - 6 if dotted else x + 6, y0 - 14), lab, size=SMALL - 2, bold=True, outline=None,
               anchor="rd" if dotted else "ld")
    band = ph / len(rows)
    for k, c in enumerate(rows):
        yc = y0 + band * (k + 0.5)
        S.text(dr, (lx0 - 12, yc), CLASS_STYLE[c]["short"], size=SMALL - 1, outline=None, anchor="rm")
        rs = [r for r in d.recs if r["class"] == c]
        zero = sum(1 for r in rs if r["clearance_deg"] == 0)
        for j, r in enumerate(rs):
            v = r["clearance_deg"]
            if not v:
                continue
            jit = ((int(r["label"]) * 2654435761) % 1000 / 1000 - 0.5) * band * 0.6
            x = px(min(max(v, 0.2), 100.0))
            col = ENV_FILL if c == SP.ENVIRONMENT else CLASS_STYLE[c]["color"]
            dr.ellipse([x - 5, yc + jit - 5, x + 5, yc + jit + 5], fill=col, outline=S.INK)
        if zero:
            S.text(dr, (lx0 + 6, yc), f"{zero} at exactly 0° (not drawn)", size=SMALL - 3, fill=S.INK2, outline=None,
                   anchor="lm")
    dr.rectangle([lx0, y0, lx0 + lw, y0 + ph], outline=S.INK2)
    S.text(dr, (lx0 + lw / 2, y0 + ph + 40), "NB1a seed interior clearance (degrees, log)", size=S.T_SMALL, fill=S.INK2,
           outline=None, anchor="ma")
    return img


def overview(d: Data) -> Image.Image:
    W, H = 3040, 2060
    img = Image.new("RGB", (W, H), S.SURFACE)
    dr = ImageDraw.Draw(img)
    n = d.summ["counts"]
    S.text(dr, (40, 28), "Natural Bootstrap-1b · foveal serviceability", size=S.T_HUGE - 12, bold=True, outline=None)
    S.text(dr, (40, 100), "Which frozen NB1a hypotheses have an existing deep-interior seed that can safely accommodate the "
           "current foveal measurement footprint?", size=S.T_BODY, fill=S.INK2, outline=None)
    S.text(dr, (40, 134), f"Read-only on the accepted NB1a products: no observation, no Blender, no controller, no seed moved, "
           f"no hypothesis changed; RGB and Blender identity did not influence selection.", size=S.T_BODY, fill=S.INK2,
           outline=None)
    xr = W - 40
    for b in BADGES["overview.png"]:
        xr = S.badge(img, xr, 34, b) - 10
    regions = [(40, 190), (1560, 190), (40, 1120), (1560, 1120)]
    RW, RH = 1440, 900
    titles = [("A · NB1a source: natural hypotheses and frozen seeds", [DER]),
              ("B · sensor geometry: the nominal core and its two disks", [DER]),
              ("C · serviceability classification", [DER]),
              ("D · reference: queued candidates", [REF, ORA])]
    for (rx, ry), (t, bs) in zip(regions, titles):
        dr.rounded_rectangle([rx - 10, ry - 10, rx + RW + 10, ry + RH], radius=10, fill=S.PANEL, outline=S.GRID)
        S.text(dr, (rx + 4, ry + 4), t, size=S.T_HEAD, bold=True, outline=None)
        xr = rx + RW
        for b in bs:
            xr = S.badge(img, xr, ry + 4, b) - 10
        dr = ImageDraw.Draw(img)
    oy = 70
    (ax, ay), (bx, by), (cx, cy), (qx, qy) = regions
    # A: NB1a hypotheses (id colours, pale) and their seeds
    col = B.id_palette(d.labels * 7919 + 13).astype(np.float32)
    col = (0.65 * col + 0.35 * 255)
    col[~d.valid] = B.NO_GEOM
    a_img = B.up(col.astype(np.uint8), SC)
    a_img[B.boundary_mask(d.labels, SC)] = S.INK
    img.paste(Image.fromarray(a_img), (ax, ay + oy))
    B.hatch_cells(img, (ax, ay + oy), ~d.valid, SC)
    dr = ImageDraw.Draw(img)
    for r in reversed(d.recs):
        s = r["seed"]
        x, y = B.xy(s["yaw_deg"], s["pitch_deg"])
        if r["cells"] == 1 or not r["clearance_deg"]:
            dr.rectangle([ax + x - 0.8, ay + oy + y - 0.8, ax + x + 0.8, ay + oy + y + 0.8], fill=S.INK)
        else:
            B.diamond(dr, ax + x, ay + oy + y, max(2.5, 3.0 + 1.6 * math.sqrt(r["clearance_deg"])))
    B.axes(dr, ax, ay + oy, PW, PH, words=True, ticks=False)
    S.text(dr, (ax, ay + oy + PH + 12), f"{len(d.recs)} accepted NB1a hypotheses (temporary, not objects); diamonds: frozen "
           "deep-interior seeds, larger with clearance; read only, never moved", size=SMALL, fill=S.INK2, outline=None)
    # B: geometry schematic and two example footprints (by rank)
    geometry_schematic(img, bx, by + oy, 420)
    ex = [r for r in example_set(d) if r["class"] in (SP.PRIMARY, SP.SECONDARY, SP.MARGINAL)][:2]
    for k, r in enumerate(ex):
        x = bx + 470 + k * 480
        img.paste(support_tile(d, r, 420), (x, by + oy))
        dr = ImageDraw.Draw(img)
        core_overlay(dr, x, by + oy, 420)
        dr.rectangle([x - 1, by + oy - 1, x + 420, by + oy + 420], outline=S.INK2)
        cap = tile_caption(r)
        S.text(dr, (x, by + oy + 430), cap[0], size=SMALL - 2, bold=True, outline=None)
        S.text(dr, (x, by + oy + 454), cap[1], size=SMALL - 3, fill=S.INK2, outline=None)
    dr = ImageDraw.Draw(img)
    blines = [f"a = CORE_FOV_DEG / 2 = {SP.R_CENTER_DEG:g}° (tools/fsg_geometry.py, sealed)",
              f"R_CENTER = 6°: the disk inscribed in the {SP.CORE_FOV_DEG:g}° square core, for every roll",
              f"R_FULL = atan(√2 · tan 6°) = {SP.R_FULL_DEG:.4f}°: the disk circumscribing the core",
              "SAFE: every 0.5° cell in the disk has range and belongs to the hypothesis",
              "a sampled support-containment test, not stereo success or visibility"]
    for k, ln in enumerate(blines):
        S.text(dr, (bx, by + oy + 500 + 34 * k), ln, size=S.T_SMALL, outline=None, bold=(k == 2))
    # C: classification
    img.paste(Image.fromarray(class_layer(d)), (cx, cy + oy))
    B.hatch_cells(img, (cx, cy + oy), ~d.valid, SC)
    stipple_cells(img, (cx, cy + oy), d.cls == SP.CLASSES.index(SP.ENVIRONMENT) + 1, SC)
    dr = ImageDraw.Draw(img)
    for r in reversed(d.recs):
        seed_glyph(dr, r, cx, cy + oy)
    for name, tag in (("primary", "P"), ("secondary", "S")):
        for r in d.queue[name][:8]:
            seed_glyph(dr, r, cx, cy + oy, rings=False, label=f"{tag}{r['queue']['rank']}")
    B.axes(dr, cx, cy + oy, PW, PH, words=True, ticks=False)
    S.text(dr, (cx, cy + oy + PH + 12), f"environment {n[SP.ENVIRONMENT]} · primary {n[SP.PRIMARY]} · secondary "
           f"{n[SP.SECONDARY]} · marginal {n[SP.MARGINAL]} · edge-only {n[SP.EDGE_ONLY]}  (total {len(d.recs)})",
           size=S.T_SMALL, bold=True, outline=None)
    legend(img, dr, cx, cy + oy + PH + 44, CLASS_LEGEND[:5])
    # D: reference (secondary): RGB crops and composition of the queue heads
    dr = ImageDraw.Draw(img)
    heads = d.queue["primary"][:5] + d.queue["secondary"][:5]
    npx = 190
    for k, r in enumerate(heads[:10]):
        x = qx + (k % 5) * (npx + 92)
        y = qy + oy + (k // 5) * (npx + 100)
        img.paste(rgb_tile(d, r, npx), (x, y))
        dr = ImageDraw.Draw(img)
        core_overlay(dr, x, y, npx)
        q = r["queue"]
        S.text(dr, (x, y + npx + 6), f"{q['name'][0].upper()}{q['rank']} {r['id']}", size=SMALL - 3, bold=True, outline=None)
        ref = d.cand_ref.get(r["id"])
        if ref:
            wtot = npx
            o0 = ref["O0_fraction"]
            cat = ref["catalog_fraction"]
            dr.rectangle([x, y + npx + 30, x + cat * wtot, y + npx + 48], fill=(133, 94, 20))
            dr.rectangle([x + cat * wtot, y + npx + 30, x + (cat + o0) * wtot, y + npx + 48], fill=(250, 240, 222),
                         outline=S.REF_BROWN)
            S.hatch(img, [x + cat * wtot, y + npx + 30, x + (cat + o0) * wtot, y + npx + 48], (200, 160, 100), spacing=5, width=1)
            dr = ImageDraw.Draw(img)
            dom = ref["dominant"]["name"] if ref["dominant"] else "—"
            S.text(dr, (x, y + npx + 54), f"O_0 {100 * o0:.0f}% · {dom[:16]}", size=SMALL - 5, fill=S.INK2, outline=None)
    if not heads:
        S.text(dr, (qx, qy + oy + 20), "no queued candidate", size=S.T_BODY, bold=True, outline=None)
    pc = d.ref["per_class"]
    ly = qy + oy + 2 * (npx + 100) + 10
    S.text(dr, (qx, ly), "Reference composition by class (post-freeze; descriptive; no effect on class or rank):",
           size=S.T_SMALL, bold=True, outline=None)
    for k, c in enumerate(SP.CLASSES):
        p = pc[c]
        txt = (f"{CLASS_STYLE[c]['short']}: {p['hypotheses']} hyp., O_0 {100 * p['O0_fraction']:.1f}% of support, "
               f"{p['hypotheses_dominated_by_O0']} dominated by O_0") if p["hypotheses"] else f"{CLASS_STYLE[c]['short']}: none"
        S.text(dr, (qx, ly + 34 + 28 * k), txt, size=SMALL, outline=None)
    S.text(dr, (qx, ly + 34 + 28 * 5 + 6), "tiles: RGB proxy (appearance only) with the core, CENTER and FULL disks; bar: "
           "catalog (brown) vs O_0 (hatched) share of the hypothesis", size=SMALL - 3, fill=S.INK2, outline=None)
    return img


# ------------------------------------------------------------------ entry
def render_all(run: Path):
    d = Data(run)
    return {"overview.png": overview(d), "serviceability-panorama.png": serviceability_panorama(d),
            "primary-look-panorama.png": look_panorama(d, "primary"),
            "secondary-look-panorama.png": look_panorama(d, "secondary"),
            "environment-candidate.png": environment_figure(d), "footprint-examples.png": footprint_examples(d),
            "class-counts.png": class_counts(d)}, d


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
    from nb1b_run import code_state
    manifest = {"schema": "NB1b-visuals-manifest-v1", "run": str(run), "sources": d.sources, "code": code_state(),
                "regenerate": f".venv/bin/python tools/natural_bootstrap/nb1b_run.py visualize --run {run} --visuals {vis}",
                "products": out,
                "glyphs": {"seed": "ink diamond", "FULL footprint": "solid ring", "CENTER footprint": "thin dotted ring",
                           "core": "square outline (tangent-plane views)",
                           "classes": {c: f"{v['short']}: colour + {v['cue']}" for c, v in CLASS_STYLE.items()},
                           "no geometry": "hatched", "reference": "brown"}}
    (vis / "visuals-manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    print(f"[nb1b] visualize: {len(FIGURES)} figures -> {vis}")
    return manifest
