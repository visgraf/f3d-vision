"""North Star-1a: the scientific visuals (Visual Language 1; deterministic PNGs).

Contract: docs/north-star/ns1a-perfect-bootstrap-round-contract.md, section 18.

- ``overview.png``: A coarse 360 RGB attention (the six frozen gazes, RGB-ONLY SELECTION); B the six raw-core RGB
  observations in frozen order; C the local perfect metric measurements with the ORACLE SEGMENTATION AID; D the
  persistent seed set in canonical H0 after six gazes.
- ``bootstrap-progression.png``: the seed set after gaze 1 ... 6 (frozen attention order).
- ``entity-seeds-3d.png``: all initialized entity geometry in H0 (three orthographic views).

Entities are distinguished by color AND a glyph AND their id label.  Pixels without a correspondence are never hidden:
no hit = dot stipple; instance 0 = cross-hatch (UNASSIGNED / NON-CATALOG ORACLE GEOMETRY); positive but not
right-visible = black diagonal hatch.  Post-freeze names appear only in the muted REFERENCE / EVALUATION column of D.
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
for _p in (HERE, HERE.parent, HERE.parent / "active_bootstrap", HERE.parent / "visual_language", HERE.parents[1]):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import ns1a_spec as SP  # noqa: E402
import style as S  # noqa: E402  (Visual Language 1, read-only)

ORA, DER, REF = SP.TRUTH_ORACLE, SP.TRUTH_DERIVED, SP.TRUTH_REFERENCE
BADGES = {"overview.png": [ORA, DER, REF], "bootstrap-progression.png": [ORA, DER], "entity-seeds-3d.png": [ORA, DER]}
LABELS = {"overview.png": [SP.LABEL_RGB, SP.LABEL_ORACLE_CORR, SP.LABEL_GEOMETRY, SP.LABEL_SEGMENTATION, SP.UNASSIGNED],
          "bootstrap-progression.png": [SP.LABEL_SEGMENTATION, SP.LABEL_GEOMETRY],
          "entity-seeds-3d.png": [SP.LABEL_SEGMENTATION, SP.LABEL_GEOMETRY]}
PALETTE = [S.OI_BLUE, S.OI_VERM, S.OI_GREEN, S.OI_PURPLE, S.OI_ORANGE, S.OI_SKY, S.WINE, S.REF_BROWN, (90, 90, 90)]
GLYPHS = ["circle", "square", "triangle", "diamond", "down", "hex"]
GAZE_COLOR = S.INK
W = 2400
MAX_POINTS = 6000
NO_HIT_BG, NOTVIS_BG, UNASSIGNED_BG = (247, 246, 242), (232, 231, 227), (244, 226, 205)


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def npz(path: Path) -> dict:
    with np.load(path, allow_pickle=False) as z:
        return {k: np.asarray(z[k]) for k in z.files}


def j(path: Path):
    return json.loads(Path(path).read_text())


def u8(rgb_linear: np.ndarray) -> np.ndarray:
    c = np.clip(np.asarray(rgb_linear, np.float64), 0.0, 1.0)
    s = np.where(c <= 0.0031308, 12.92 * c, 1.055 * np.power(c, 1 / 2.4) - 0.055)
    return np.round(255 * s).astype(np.uint8)


def ent_style(k: int, order: list[int]) -> tuple[tuple, str]:
    i = order.index(k)
    return PALETTE[i % len(PALETTE)], GLYPHS[(i // len(PALETTE)) % len(GLYPHS)]


def glyph(d: ImageDraw.ImageDraw, x: float, y: float, kind: str, color, r: float = 9, outline=S.WHITE,
          hollow: bool = False) -> None:
    if kind == "circle":
        pts = None
        box = [x - r, y - r, x + r, y + r]
        if hollow:
            d.ellipse(box, outline=color, width=3)
        else:
            d.ellipse(box, fill=color, outline=outline, width=2)
        return
    if kind == "square":
        pts = [(x - r, y - r), (x + r, y - r), (x + r, y + r), (x - r, y + r)]
    elif kind == "triangle":
        pts = [(x, y - r * 1.2), (x + r * 1.1, y + r * 0.8), (x - r * 1.1, y + r * 0.8)]
    elif kind == "down":
        pts = [(x, y + r * 1.2), (x + r * 1.1, y - r * 0.8), (x - r * 1.1, y - r * 0.8)]
    elif kind == "diamond":
        pts = [(x, y - r * 1.25), (x + r * 1.25, y), (x, y + r * 1.25), (x - r * 1.25, y)]
    else:  # hex
        pts = [(x + r * 1.1 * math.cos(a), y + r * 1.1 * math.sin(a)) for a in np.arange(6) * math.pi / 3]
    if hollow:
        d.polygon(pts, outline=color, width=3)
    else:
        d.polygon(pts, fill=color, outline=outline, width=2)


class Data:
    def __init__(self, run: Path) -> None:
        self.run = run
        self.gazes = j(run / "source/nb1c-gaze-list.json")["gazes"]
        self.seedset = j(run / "seeds/seed-set.json")
        self.ev = j(run / "evaluation/evaluation.json")
        self.history = j(run / "seeds/construction-history.json")["history"]
        self.order = [e["temporary_entity_id"] for e in self.seedset["entities"]]
        self.names = {e["temporary_entity_id"]: e["post_freeze_name"] for e in self.ev["entities"]}
        self.ents = {e["temporary_entity_id"]: e for e in self.seedset["entities"]}
        self.pano = npz(SP.NB1A_RGB[0])["srgb8"]
        self.cal, self.rgb, self.cls, self.prod, self.geo, self.ids, self.osum = {}, {}, {}, {}, {}, {}, {}
        for g in self.gazes:
            r = g["rank"]
            rd = SP.rank_dir(r)
            self.cal[r] = j(run / SP.acq_rel(r, "calibration.json"))
            self.rgb[r] = npz(run / SP.acq_rel(r, "rgb-observation.npz"))["rgb_L"]
            self.cls[r] = npz(run / f"correspondence/{rd}/core-class-map.npz")["core_class"]
            self.prod[r] = npz(run / f"correspondence/{rd}/oracle-correspondences.npz")
            e = npz(run / f"geometry/{rd}/epipolar-result.npz")
            self.geo[r] = {"P_epi": e["P_epi"], "valid": e["valid_epi"], "range_L": e["range_L"]}
            self.ids[r] = npz(run / f"segmentation/{rd}/local-identity.npz")["temporary_entity_id"]
            self.osum[r] = j(run / f"correspondence/{rd}/oracle-summary.json")
        import ns1a_run as R
        self.maps = R.load_maps(run / "seeds/entity-maps.npz")
        self.snaps = {g["rank"]: R.load_maps(run / f"seeds/snapshot-after-{SP.rank_dir(g['rank'])}.npz")
                      for g in self.gazes}


# ------------------------------------------------------------------ shared drawing helpers
def header(img: Image.Image, title: str, lines: list[str], badges: list[str]) -> int:
    d = ImageDraw.Draw(img)
    S.text(d, (40, 26), title, size=S.T_TITLE, bold=True)
    y = 70
    for ln in lines:
        S.text(d, (40, y), ln, size=S.T_SMALL, fill=S.INK2)
        y += 27
    x = W - 40
    for b in reversed(badges):
        x = S.badge(img, x, 24, b) - 12
    return y + 8


def panel_title(img: Image.Image, y: int, letter: str, title: str, tags: list[str] = ()) -> int:
    d = ImageDraw.Draw(img)
    d.rectangle([30, y, W - 30, y + 44], fill=(236, 235, 230))
    S.text(d, (44, y + 9), f"{letter} — {title}", size=S.T_HEAD, bold=True, outline=None)
    x = W - 44
    for t in reversed(list(tags)):
        f = S.font(S.T_SMALL, True)
        w = d.textlength(t, font=f) + 20
        d.rounded_rectangle([x - w, y + 8, x, y + 36], radius=5, fill=S.WHITE, outline=S.INK2, width=2)
        d.text((x - w + 10, y + 11), t, font=f, fill=S.INK)
        x -= w + 10
    panel_title.left = x
    return y + 54


def pano_xy(yaw: float, pitch: float, w: int, h: int) -> tuple[float, float]:
    return (yaw + 180.0) / 360.0 * w, (90.0 - pitch) / 180.0 * h


def core_outline(c: dict) -> np.ndarray:
    """Head-frame yaw / pitch (deg) of the left raw-core border pixel rays (calibration only)."""
    import fsg_geometry as FG
    a, b = SP.CORE_ORIGIN, SP.CORE_ORIGIN + SP.CORE_SIZE - 1
    t = np.linspace(a, b, 64)
    pts = np.concatenate([np.c_[t, np.full(64, a)], np.c_[np.full(64, b), t], np.c_[t[::-1], np.full(64, b)],
                          np.c_[np.full(64, a), t[::-1]]])
    d = FG.rays_h(c["eyes"][0], pts)
    yaw = np.degrees(np.arctan2(d[:, 0], -d[:, 2]))
    pitch = np.degrees(np.arcsin(np.clip(d[:, 1], -1, 1)))
    return np.c_[yaw, pitch]


def draw_core_polygon(d: ImageDraw.ImageDraw, yp: np.ndarray, w: int, h: int, ox: int, oy: int, color, width=3):
    xy = np.array([pano_xy(a, b, w, h) for a, b in yp])
    if xy[:, 0].max() - xy[:, 0].min() > w / 2:          # straddles the longitude seam: draw both copies
        xy[:, 0] = np.where(xy[:, 0] < w / 2, xy[:, 0] + w, xy[:, 0])
        copies = (0.0, -float(w))
    else:
        copies = (0.0,)
    for s in copies:
        pts = [(ox + x + s, oy + y) for x, y in xy]
        d.line(pts + [pts[0]], fill=S.WHITE, width=width + 4)
        d.line(pts + [pts[0]], fill=color, width=width)


def core_rgb_tile(rgb_l: np.ndarray, size: int) -> Image.Image:
    a = SP.CORE_ORIGIN
    core = u8(rgb_l[a:a + SP.CORE_SIZE, a:a + SP.CORE_SIZE])
    return Image.fromarray(core).resize((size, size), Image.NEAREST)


def mask_image(mask_core: np.ndarray, size: int) -> Image.Image:
    return Image.fromarray((np.asarray(mask_core, bool) * 255).astype(np.uint8)).resize((size, size), Image.NEAREST)


def class_overlays(img: Image.Image, cls: np.ndarray, x: int, y: int, size: int) -> None:
    """Never hide a non-correspondence pixel: stipple (no hit), cross-hatch (instance 0), black hatch (not visible)."""
    box = [x, y, x + size, y + size]
    big = Image.new("L", img.size, 0)
    for k, painter in ((SP.CLASS_NO_HIT, "stipple"), (SP.CLASS_INSTANCE0, "cross"), (SP.CLASS_NOT_VISIBLE, "hatch")):
        m = cls == k
        if not m.any():
            continue
        mi = mask_image(m, size)
        big.paste(0, (0, 0, img.size[0], img.size[1]))
        big.paste(mi, (x, y))
        if painter == "stipple":
            layer = Image.new("RGB", img.size, NO_HIT_BG)
            S.stipple(layer, box, color=S.STIPPLE, spacing=7, r=1)
            img.paste(layer.crop(box), (x, y), mi)
        elif painter == "cross":
            S.hatch(img, box, S.OI_ORANGE, spacing=9, width=2, cross=True, mask=big)
        else:
            S.hatch(img, box, S.INK, spacing=8, width=2, mask=big)


def entity_tile(dd: Data, r: int, size: int) -> tuple[Image.Image, dict]:
    """The core at gaze r: each perfect correspondence colored by its ORACLE id, shaded by measured range."""
    cls = dd.cls[r]
    base = np.zeros((SP.CORE_SIZE, SP.CORE_SIZE, 3), np.uint8)
    base[...] = NO_HIT_BG
    base[cls == SP.CLASS_INSTANCE0] = UNASSIGNED_BG
    base[cls == SP.CLASS_NOT_VISIBLE] = NOTVIS_BG
    rows, cols = dd.prod[r]["left_core_row"], dd.prod[r]["left_core_col"]
    ids, rng = dd.ids[r], dd.geo[r]["range_L"]
    cent = {}
    for k in sorted(set(int(v) for v in ids if v > 0)):
        m = ids == k
        col, _g = ent_style(k, dd.order)
        rr = np.clip((rng[m] - 0.5) / 5.5, 0, 1)[:, None]
        shade = (np.asarray(col, float)[None, :] * (1.0 - 0.45 * rr) + 255 * 0.45 * (1 - rr) * 0.35).clip(0, 255)
        base[rows[m], cols[m]] = shade.astype(np.uint8)
        cent[k] = (float(np.median(cols[m])), float(np.median(rows[m])), int(m.sum()))
    tile = Image.fromarray(base).resize((size, size), Image.NEAREST)
    return tile, cent


def place_label(px: float, py: float, w: float, h: float, placed: list, box) -> tuple[float, float]:
    """Move a label down (then up) in fixed steps until it overlaps no placed label; presentation only."""
    x0, y0, x1, y1 = box
    for k in range(0, 40):
        dy = (k // 2 + 1) * h * (1 if k % 2 == 0 else -1) if k else 0.0
        ly = min(max(py + dy, y0 + 2), y1 - h - 2)
        lx = min(max(px, x0 + 2), x1 - w - 2)
        if not any(lx < a + aw and a < lx + w and ly < b + bh and b < ly + h for a, b, aw, bh in placed):
            placed.append((lx, ly, w, h))
            return lx, ly
    placed.append((px, py, w, h))
    return px, py


def top_view(img: Image.Image, box, maps: dict, dd: Data, extent: float, new: set = frozenset(),
             fused: set = frozenset(), seen_only: dict | None = None, gaze_lines: bool = True, small: bool = False,
             view: str = "top") -> None:
    """Orthographic H0 view of entity maps. view: top (X right, -Z up), front (X right, Y up), side (-Z right, Y up)."""
    x0, y0, x1, y1 = box
    d = ImageDraw.Draw(img)
    d.rectangle(box, fill=S.PANEL, outline=S.FAINT, width=2)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    s = (min(x1 - x0, y1 - y0) / 2 - 18) / extent

    def proj(p):
        p = np.asarray(p, float).reshape(-1, 3)
        if view == "top":
            u, v = p[:, 0], -p[:, 2]
        elif view == "front":
            u, v = p[:, 0], p[:, 1]
        else:
            u, v = -p[:, 2], p[:, 1]
        return cx + s * u, cy - s * v

    for rr in (1.0, 2.0, 3.0, 4.0, 5.0, 6.0):
        if rr <= extent:
            d.ellipse([cx - s * rr, cy - s * rr, cx + s * rr, cy + s * rr], outline=S.GRID, width=1)
            if not small:
                S.text(d, (cx + s * rr * 0.707 + 4, cy - s * rr * 0.707 - 18), f"{rr:.0f} m", size=15, fill=S.MUTED,
                       outline=None)
    if gaze_lines:
        for g in dd.gazes:
            y, p = math.radians(g["yaw_deg"]), math.radians(g["pitch_deg"])
            dv = np.array([math.sin(y) * math.cos(p), math.sin(p), -math.cos(y) * math.cos(p)])
            ex, ey = proj(dv * extent * 0.92)
            S.dashed_line(d, [(cx, cy), (float(ex[0]), float(ey[0]))], S.MUTED, width=2, dash=8, gap=6)
            S.text(d, (float(ex[0]) - 8, float(ey[0]) - 12), str(g["rank"]), size=15 if small else S.T_SMALL,
                   bold=True, fill=S.INK2)
    for k in sorted(maps):
        col, gk = ent_style(k, dd.order)
        xyz = np.asarray(maps[k]["xyz_h"], float)
        idx = np.linspace(0, len(xyz) - 1, min(len(xyz), MAX_POINTS)).astype(int)
        u, v = proj(xyz[idx])
        ok = (u > x0 + 2) & (u < x1 - 2) & (v > y0 + 2) & (v < y1 - 2)
        for a, b in zip(u[ok], v[ok]):
            d.rectangle([a - 1, b - 1, a + 1, b + 1], fill=col)
    placed: list = []
    fs = 14 if small else 17
    labels = []
    for k in sorted(maps):
        col, gk = ent_style(k, dd.order)
        c = np.median(np.asarray(maps[k]["xyz_h"], float), axis=0)
        a, b = proj(c)
        a, b = float(np.clip(a[0], x0 + 14, x1 - 14)), float(np.clip(b[0], y0 + 14, y1 - 14))
        glyph(d, a, b, gk, col, r=7 if small else 9)
        if k in new:
            S.ring(d, a, b, r=17 if small else 21, color=S.INK, width=3)
        if k in fused:
            S.text(d, (a - 5, b - 34), "+", size=S.T_SMALL, bold=True)
        labels.append((a + 12, b - 9, str(k), col, True))
    for k, c in (seen_only or {}).items():
        col, gk = ent_style(k, dd.order)
        a, b = proj(c)
        a, b = float(np.clip(a[0], x0 + 14, x1 - 14)), float(np.clip(b[0], y0 + 14, y1 - 14))
        glyph(d, a, b, gk, col, r=6 if small else 8, hollow=True)
        if not small:                                  # small panels: hollow glyphs only (counts below)
            labels.append((a + 10, b - 9, str(k), col, False))
    for lx, ly, s, col, bold in labels:
        w = d.textlength(s, font=S.font(fs, bold)) + 4
        qx, qy = place_label(lx, ly, w, fs + 4, placed, box)
        if abs(qy - ly) > 1:
            d.line([lx - 3, ly + fs / 2 + 2, qx, qy + fs / 2], fill=S.FAINT, width=1)
        S.text(d, (qx, qy), s, size=fs, bold=bold, fill=col)
    d.polygon([(cx, cy - 9), (cx + 7, cy + 6), (cx - 7, cy + 6)], fill=S.INK)
    if not small:
        S.text(d, (cx + 10, cy + 2), "head (H0)", size=15, fill=S.INK2, outline=S.WHITE)


def seen_only_centroids(dd: Data, upto: int | None = None) -> dict:
    out = {}
    for k, e in dd.ents.items():
        if e["initialized"] and (upto is None or e["initialized_at_rank"] <= upto):
            continue
        pts = []
        for r in e["gaze_ranks_seen"]:
            if upto is not None and r > upto:
                continue
            m = (dd.ids[r] == k) & dd.geo[r]["valid"]
            pts.append(dd.geo[r]["P_epi"][m])
        if pts and sum(len(p) for p in pts):
            out[k] = np.median(np.vstack(pts), axis=0)
    return out


def extent_of(dd: Data) -> float:
    allp = [np.asarray(m["xyz_h"], float) for m in dd.maps.values()]
    if not allp:
        return 4.0
    p = np.vstack(allp)
    return float(min(7.0, max(1.5, np.quantile(np.linalg.norm(p[:, [0, 2]], axis=1), 0.995) * 1.08)))


# ------------------------------------------------------------------ overview
def overview(dd: Data) -> tuple[Image.Image, dict]:
    sc = dd.seedset["counts"]
    n_rows = max(12, len(dd.order))
    table_h = 120 + 30 * n_rows
    h_d = max(980, table_h + 260)
    H = 200 + 990 + 520 + 560 + h_d + 40
    img = Image.new("RGB", (W, H), S.SURFACE)
    y = header(img, "North Star-1a — RGB bootstrap → PERFECT local measurement → persistent entity seeds", [
        "Classroom · fixed head · static scene · the six frozen NB1c RGB gazes executed ONCE each, in frozen order · "
        "4096 spp · OPTIX · seeds L 2111 / R 2112",
        "PERFECT / ORACLE correspondence (accepted AB1b) → DERIVED spherical geometry (accepted AB1b) → ORACLE "
        "SEGMENTATION AID (local Object Index) → accepted fsg3 surface map (≥ 100 pts, 12 mm, 12 mm)",
        "NO global catalog before the seed freeze · NO controller · NO FSG6f · NO seventh gaze · natural stereo "
        "DEFERRED"], BADGES["overview.png"])
    d = ImageDraw.Draw(img)
    panels = {}
    # ---- A
    y = panel_title(img, y + 4, "A", "COARSE 360 RGB ATTENTION (accepted NB1c, frozen)", [SP.LABEL_RGB, "no depth",
                                                                                          "no Blender identity"])
    pw, ph = 1800, 900
    pano = Image.fromarray(dd.pano).resize((pw, ph), Image.BICUBIC)
    layer = pano.copy()
    ld = ImageDraw.Draw(layer)
    for g in dd.gazes:
        draw_core_polygon(ld, core_outline(dd.cal[g["rank"]]), pw, ph, 0, 0, S.CORE_GREEN, width=3)
    for g in dd.gazes:
        gx, gy = pano_xy(g["yaw_deg"], g["pitch_deg"], pw, ph)
        S.crosshair(ld, gx, gy, r=11, color=GAZE_COLOR)
        lx = gx + 26 if gx < pw - 70 else gx - 56
        S.text(ld, (lx, gy - 46), str(g["rank"]), size=S.T_BIG, bold=True, plate=S.WHITE)
    img.paste(layer, (40, y))
    d = ImageDraw.Draw(img)
    d.rectangle([40, y, 40 + pw, y + ph], outline=S.INK2, width=2)
    S.badge(img, 40 + pw - 8, y + 8, ORA)
    xs = 40 + pw + 30
    S.text(d, (xs, y + 4), "Frozen attention order", size=S.T_HEAD, bold=True)
    S.text(d, (xs, y + 40), "NB1c freeze 87a3bab0 · consumed as-is", size=S.T_SMALL, fill=S.INK2)
    yy = y + 84
    for g in dd.gazes:
        S.text(d, (xs, yy), f"{g['rank']}", size=S.T_BIG, bold=True)
        S.text(d, (xs + 44, yy + 2), f"yaw {g['yaw_deg']:+.2f}°", size=S.T_BODY)
        S.text(d, (xs + 44, yy + 30), f"pitch {g['pitch_deg']:+.2f}°", size=S.T_BODY)
        S.text(d, (xs + 250, yy + 16), f"row {g['row']}, col {g['col']}", size=S.T_SMALL, fill=S.MUTED)
        yy += 70
    yy += 10
    for ln in ["Cross-hair = executed fixation;", "green outline = the 12° raw", "measuring core (left eye).",
               "No reselection · no filtering ·", "no replacement · no 7th gaze.", "Six gazes = an ATTENTION",
               "BUDGET, not an object count."]:
        S.text(d, (xs, yy), ln, size=S.T_SMALL, fill=S.INK2)
        yy += 26
    panels["A"] = [g["rank"] for g in dd.gazes]
    y += ph + 16
    # ---- B
    yb = y
    y = panel_title(img, y, "B", "SIX FOVEAL OBSERVATIONS (raw left 12° core, frozen order)", ["4096 spp",
                                                                                               "one look per gaze"])
    S.badge(img, panel_title.left - 6, yb + 7, ORA, size=16)
    tile, gap = 340, 52
    for i, g in enumerate(dd.gazes):
        r = g["rank"]
        x = 40 + i * (tile + gap)
        img.paste(core_rgb_tile(dd.rgb[r], tile), (x, y))
        d = ImageDraw.Draw(img)
        d.rectangle([x, y, x + tile, y + tile], outline=S.CORE_GREEN, width=3)
        S.text(d, (x + 8, y + 6), f"{r}", size=S.T_BIG, bold=True, plate=S.WHITE)
        o = dd.osum[r]
        S.text(d, (x, y + tile + 8), f"yaw {g['yaw_deg']:+.2f}°  pitch {g['pitch_deg']:+.2f}°", size=S.T_SMALL)
        S.text(d, (x, y + tile + 34), f"perfect corr. {o['correspondences']:,} ({100 * o['fraction_of_core']:.1f} %)",
               size=S.T_SMALL, bold=True)
        S.text(d, (x, y + tile + 60), f"instance-0 excluded {o['instance_0']['id_0_hits']:,}", size=S.T_SMALL,
               fill=S.OI_VERM if o['instance_0']['id_0_hits'] else S.INK2)
        S.text(d, (x, y + tile + 86), f"no hit {o['excluded']['no_finite_hit']:,} · not visible "
                                      f"{o['excluded']['different_right_instance']:,}", size=S.T_SMALL, fill=S.INK2)
    panels["B"] = [g["rank"] for g in dd.gazes]
    y += tile + 130
    # ---- C
    y = panel_title(img, y, "C", "LOCAL PERFECT METRIC MEASUREMENTS (per gaze; identity is an oracle aid)",
                    [SP.LABEL_ORACLE_CORR, SP.LABEL_GEOMETRY, SP.LABEL_SEGMENTATION])
    for i, g in enumerate(dd.gazes):
        r = g["rank"]
        x = 40 + i * (tile + gap)
        t, cent = entity_tile(dd, r, tile)
        img.paste(t, (x, y))
        class_overlays(img, dd.cls[r], x, y, tile)
        d = ImageDraw.Draw(img)
        placed: list[tuple[float, float]] = []
        for k, (cu, cv, n) in sorted(cent.items(), key=lambda kv: -kv[1][2]):
            if n < 400:
                continue
            col, gk = ent_style(k, dd.order)
            px, py = x + (cu + 0.5) * tile / SP.CORE_SIZE, y + (cv + 0.5) * tile / SP.CORE_SIZE
            if px < x + 64 and py < y + 64:               # keep clear of the rank plate
                px, py = x + 70, y + 30
            while any(abs(px - a) < 60 and abs(py - b) < 26 for a, b in placed) and py < y + tile - 30:
                py += 28                                   # deterministic: move down until clear
            placed.append((px, py))
            glyph(d, px, py, gk, col, r=8)
            S.text(d, (px + 11, py - 10), str(k), size=17, bold=True, plate=S.WHITE)
        d.rectangle([x, y, x + tile, y + tile], outline=S.CORE_GREEN, width=3)
        S.text(d, (x + 8, y + 6), f"{r}", size=S.T_BIG, bold=True, plate=S.WHITE)
        ents = sorted(cent.items(), key=lambda kv: -kv[1][2])
        here = [e for e in dd.history if e["rank"] == r]
        ninit = sum(e["action"] == "INITIALIZED" for e in here)
        nfuse = sum(e["action"] == "FUSED" for e in here)
        S.text(d, (x, y + tile + 8), f"{len(ents)} local ids · {ninit} initialized · {nfuse} fused", size=S.T_SMALL,
               bold=True)
        parts = [f"{k}:{n / 1000:.1f}k" if n >= 1000 else f"{k}:{n}" for k, (_a, _b, n) in ents]
        line, f17 = "", S.font(17)
        for i_p, part in enumerate(parts):
            more = f" +{len(parts) - i_p} more"
            cand = (line + " " + part).strip()
            if d.textlength(cand + (more if i_p < len(parts) - 1 else ""), font=f17) > tile:
                line += more
                break
            line = cand
        S.text(d, (x, y + tile + 34), line, size=17, fill=S.INK2)
        rq = np.quantile(dd.geo[r]["range_L"][dd.geo[r]["valid"]], [0.5]) if dd.geo[r]["valid"].any() else [np.nan]
        S.text(d, (x, y + tile + 58), f"median range {rq[0]:.2f} m" if np.isfinite(rq[0]) else "no measured geometry",
               size=17, fill=S.INK2)
    yl = y + tile + 92
    d = ImageDraw.Draw(img)
    lx = 40
    for label, kind in (("perfect correspondence: color = oracle id (glyph + id), shade = range", "fill"),
                        ("no geometric hit", "stipple"), (SP.UNASSIGNED + " (instance 0)", "cross"),
                        ("positive id, not right-visible", "hatch")):
        sw = Image.new("RGB", (46, 26), S.PANEL)
        if kind == "fill":
            sw.paste(PALETTE[0], (0, 0, 23, 26))
            sw.paste(PALETTE[1], (23, 0, 46, 26))
        elif kind == "stipple":
            sw.paste(NO_HIT_BG, (0, 0, 46, 26))
            S.stipple(sw, (0, 0, 46, 26), spacing=7)
        elif kind == "cross":
            sw.paste(UNASSIGNED_BG, (0, 0, 46, 26))
            S.hatch(sw, (0, 0, 46, 26), S.OI_ORANGE, spacing=9, cross=True)
        else:
            sw.paste(NOTVIS_BG, (0, 0, 46, 26))
            S.hatch(sw, (0, 0, 46, 26), S.INK, spacing=8)
        img.paste(sw, (lx, yl))
        d = ImageDraw.Draw(img)
        d.rectangle([lx, yl, lx + 46, yl + 26], outline=S.INK2, width=1)
        S.text(d, (lx + 54, yl + 2), label, size=17)
        lx += 54 + int(d.textlength(label, font=S.font(17))) + 40
    panels["C"] = [g["rank"] for g in dd.gazes]
    y += tile + 140
    # ---- D
    y = panel_title(img, y, "D", "PERSISTENT SEED SET — canonical H0, after the six gazes (top view)",
                    [SP.LABEL_SEGMENTATION, "accepted fsg3 map"])
    vb = (40, y, 40 + 980, y + 980)
    top_view(img, vb, dd.maps, dd, extent_of(dd), seen_only=seen_only_centroids(dd))
    d = ImageDraw.Draw(img)
    S.text(d, (vb[0] + 12, vb[1] + 10), "X right · −Z (forward) up · filled glyph = initialized map;", size=17,
           fill=S.INK2, outline=S.WHITE)
    S.text(d, (vb[0] + 12, vb[1] + 34), "hollow glyph = seen, not initialized (< 100 pts); dashed = gaze", size=17,
           fill=S.INK2, outline=S.WHITE)
    xt = 1060
    S.text(d, (xt, y + 4), f"initialized entities: {sc['initialized']}", size=S.T_HEAD, bold=True)
    S.text(d, (xt + 420, y + 4), f"seen but not initialized: {sc['seen_but_not_initialized']}", size=S.T_HEAD,
           bold=True, fill=S.INK2)
    un = dd.seedset["unassigned_instance_0"]["per_rank"]
    S.text(d, (xt, y + 42), "instance 0 (UNASSIGNED / NON-CATALOG) hits / finite hits per gaze:", size=S.T_SMALL)
    S.text(d, (xt, y + 68), "   ".join(f"{r}: {un[str(r)]['id_0_hits']:,}/{un[str(r)]['finite_left_hits']:,}"
                                       for r in SP.RANKS), size=S.T_SMALL, fill=S.OI_VERM)
    cols = [("", 0), ("id", 34), ("first", 120), ("ranks seen", 196), ("init@", 360), ("final surfels", 440),
            ("patches", 600), ("raw pts", 700), ("post-freeze name", 830)]
    ty = y + 112
    for name, dx in cols:
        S.text(d, (xt + dx, ty), name, size=S.T_SMALL, bold=True, fill=S.REF_BROWN if "name" in name else S.INK)
    S.badge(img, W - 40, ty - 6, REF, size=15)
    ty += 34
    d.line([xt, ty - 4, W - 40, ty - 4], fill=S.FAINT, width=2)
    for k in dd.order:
        e = dd.ents[k]
        col, gk = ent_style(k, dd.order)
        glyph(d, xt + 12, ty + 11, gk, col, r=8, hollow=not e["initialized"])
        vals = [str(k), str(e["first_seen_rank"]), ",".join(str(r) for r in e["gaze_ranks_seen"]),
                "—" if not e["initialized"] else str(e["initialized_at_rank"]), f"{e['final_surfels']:,}",
                str(e["contributing_patches"]), f"{e['total_raw_measured_points']:,}"]
        for (name, dx), v in zip(cols[1:8], vals):
            S.text(d, (xt + dx, ty), v, size=S.T_SMALL, bold=name == "id", fill=S.INK if e["initialized"] else S.MUTED)
        nm = dd.names.get(k) or "—"
        S.text(d, (xt + cols[8][1], ty), nm[:26], size=S.T_SMALL, fill=S.REF_BROWN)
        ty += 30
    panels["D"] = list(dd.order)
    return img, {"panels": panels}


# ------------------------------------------------------------------ bootstrap progression
def progression(dd: Data) -> tuple[Image.Image, dict]:
    tile, gap = 360, 32
    H = 200 + 60 + 260 + 30 + tile + 220
    img = Image.new("RGB", (W, H), S.SURFACE)
    y = header(img, "North Star-1a — the seed set after gaze 1 … 6 (frozen attention order)", [
        "Top: the raw left core executed at that step (4096 spp). Bottom: all persistent entity maps so far, canonical "
        "H0 top view (X right, −Z up), same scale in every column.",
        "Ring = initialized at this gaze · '+' = fused at this gaze · hollow = seen, not initialized (< 100 pts). "
        "Identity is the ORACLE SEGMENTATION AID; geometry is DERIVED (accepted AB1b)."], BADGES["bootstrap-progression.png"])
    ext = extent_of(dd)
    x0 = 40
    for i, g in enumerate(dd.gazes):
        r = g["rank"]
        x = x0 + i * (tile + gap)
        d = ImageDraw.Draw(img)
        S.text(d, (x, y + 4), f"after gaze {r}", size=S.T_HEAD, bold=True)
        S.text(d, (x + 200, y + 8), f"({g['yaw_deg']:+.1f}°, {g['pitch_deg']:+.1f}°)", size=S.T_SMALL, fill=S.INK2)
        th = 250
        img.paste(core_rgb_tile(dd.rgb[r], th), (x + (tile - th) // 2, y + 44))
        d = ImageDraw.Draw(img)
        d.rectangle([x + (tile - th) // 2, y + 44, x + (tile + th) // 2, y + 44 + th], outline=S.CORE_GREEN, width=3)
        here = [e for e in dd.history if e["rank"] == r]
        new = {e["entity"] for e in here if e["action"] == "INITIALIZED"}
        fused = {e["entity"] for e in here if e["action"] == "FUSED"}
        vy = y + 44 + th + 20
        top_view(img, (x, vy, x + tile, vy + tile), dd.snaps[r], dd, ext, new=new, fused=fused,
                 seen_only=seen_only_centroids(dd, upto=r), small=True)
        d = ImageDraw.Draw(img)
        upto = [e for e in dd.history if e["rank"] <= r]
        ninit = len({e["entity"] for e in upto if e["action"] == "INITIALIZED"})
        seen = {e["entity"] for e in upto}
        surf = sum(len(m["xyz_h"]) for m in dd.snaps[r].values())
        S.text(d, (x, vy + tile + 10), f"initialized so far: {ninit}", size=S.T_SMALL, bold=True)
        S.text(d, (x, vy + tile + 36), f"seen, not initialized: {len(seen) - ninit}", size=S.T_SMALL, fill=S.INK2)
        S.text(d, (x, vy + tile + 62), f"surfels: {surf:,}", size=S.T_SMALL, fill=S.INK2)
        S.text(d, (x, vy + tile + 88), "new: " + (",".join(str(k) for k in sorted(new)) or "—"), size=S.T_SMALL)
        S.text(d, (x, vy + tile + 114), "fused: " + (",".join(str(k) for k in sorted(fused)) or "—"), size=S.T_SMALL)
        if i < len(dd.gazes) - 1:
            S.arrow(d, x + tile + 4, vy + tile / 2, x + tile + gap - 4, vy + tile / 2, width=3, head=12)
    return img, {"panels": {"columns": [g["rank"] for g in dd.gazes]}}


# ------------------------------------------------------------------ 3-D entity seeds
def seeds_3d(dd: Data) -> tuple[Image.Image, dict]:
    v = 740
    n_rows = len(dd.order)
    H = 200 + v + 80 + 40 + 30 * ((n_rows + 2) // 3) + 60
    img = Image.new("RGB", (W, H), S.SURFACE)
    y = header(img, "North Star-1a — initialized persistent entity geometry in canonical H0 (orthographic views)", [
        "All initialized entity maps after the six gazes (accepted fsg3 surface map; DERIVED spherical geometry from "
        "PERFECT / ORACLE correspondence). Color + glyph + id = the temporary entity (ORACLE SEGMENTATION AID).",
        "Head at the origin; +X right, +Y up, −Z forward; metres. Up to 6,000 surfels drawn per entity (uniform "
        "subsample, deterministic)."], BADGES["entity-seeds-3d.png"])
    ext = extent_of(dd)
    for i, (view, title) in enumerate((("top", "TOP (X right, −Z up)"), ("front", "FRONT (X right, Y up)"),
                                       ("side", "SIDE (−Z right, Y up)"))):
        x = 40 + i * (v + 30)
        d = ImageDraw.Draw(img)
        S.text(d, (x, y + 4), title, size=S.T_HEAD, bold=True)
        top_view(img, (x, y + 40, x + v, y + 40 + v), dd.maps, dd, ext, gaze_lines=view == "top", view=view)
    d = ImageDraw.Draw(img)
    ty = y + 40 + v + 30
    for i, k in enumerate([k for k in dd.order if dd.ents[k]["initialized"]]):
        e = dd.ents[k]
        col, gk = ent_style(k, dd.order)
        cx = 40 + (i % 3) * 780
        cy = ty + (i // 3) * 30
        glyph(d, cx + 12, cy + 11, gk, col, r=8)
        S.text(d, (cx + 30, cy), f"{k}: {e['final_surfels']:,} surfels · ranks {','.join(map(str, e['gaze_ranks_seen']))}"
                                 f" · init@{e['initialized_at_rank']}", size=S.T_SMALL)
    return img, {"panels": {"views": ["top", "front", "side"]}}


FIGURE_FUNCS = {"overview.png": overview, "bootstrap-progression.png": progression, "entity-seeds-3d.png": seeds_3d}


def render_all(run: Path) -> tuple[dict, Data]:
    dd = Data(run)
    return {n: f(dd) for n, f in FIGURE_FUNCS.items()}, dd


def visualize(run: Path, vis: Path) -> dict:
    vis.mkdir(parents=True, exist_ok=True)
    figs, dd = render_all(run)
    man = {"schema": "NS1a-visuals-v1", "experiment": SP.EXPERIMENT, "visual_language": "Visual Language 1",
           "fonts": S.font_hashes(), "frozen_gaze_order": [g["rank"] for g in dd.gazes],
           "displays": {"no_hit": "dot stipple (never hidden)", "instance_0": "orange cross-hatch: " + SP.UNASSIGNED,
                        "not_visible": "black diagonal hatch", "entity": "color + glyph + id label (non-color cue)",
                        "names": "post-freeze only, muted REFERENCE / EVALUATION column (overview D)"},
           "figures": {}}
    for name, (img, meta) in figs.items():
        path = vis / name
        img.save(path, format="PNG", optimize=False)
        man["figures"][name] = {"sha256": sha256(path), "size": list(img.size), "badges": BADGES[name],
                                "labels": LABELS[name], **meta}
    (vis / "visuals-manifest.json").write_text(json.dumps(man, indent=1, sort_keys=True) + "\n")
    return man
