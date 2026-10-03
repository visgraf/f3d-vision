"""Active Bootstrap-1a: the persistent human-facing figures of the first natural stereo look.

Contract: docs/active-bootstrap/ab1a-first-natural-stereo-look-contract.md, section 12.  Reads the saved run
(calibration, the RGB observation, the pre-look record, the frozen natural measurement and the post-freeze evaluation)
and the accepted coarse spherical RGB proxy.  Draws with the accepted Visual Language 1 style (read-only).

Truth classes: ORACLE INPUT (rendered RGB), DERIVED (calibration geometry, rectification, natural disparity / validity
/ range / points), REFERENCE / EVALUATION (Position, Object Index, oracle geometry, errors).  Nothing is
CONTROLLER-TIME.  Glyphs: solid crosshair = the executed gaze (frozen NB1c RGB gaze #1); hollow square = the
calibration-derived direction of the rectified core centre; x = the baseline direction (epipole); dashed square = the
nominal 12-degree raw core; small solid box = the raw source of the rectified core.  Empty results are drawn as
explicit statements.  Deterministic: the checker regenerates every PNG byte-identically.
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
for p in (HERE, TOOLS, TOOLS / "classroom_oracle", TOOLS / "visual_language"):
    sys.path.insert(0, str(p))

import ab1a_spec as SP  # noqa: E402
import breadth1_visuals as B  # noqa: E402  (accepted Breadth-1 panorama helpers, read-only)
import fsg_geometry as FG  # noqa: E402  (accepted, read-only)
import style as S  # noqa: E402  (Visual Language 1, read-only)

ORA, DER, REF = SP.TRUTH_ORACLE, SP.TRUTH_DERIVED, SP.TRUTH_REFERENCE
COARSE_RGB = (SP.SHARED / "previews/natural-bootstrap-1a-range-connectivity/input/rgb-sensory.npz",
              "cd2600e678fe7f33471e50bee5443128dd5470cc2b380eb7b34a22d3e4ad2c3e")
SMALL = 17
FIGURES = ["overview.png", "binocular-pair.png", "tangent-geometry.png", "natural-disparity.png",
           "natural-validity.png", "natural-range.png", "measured-point-cloud.png", "reference-error.png",
           "reference-composition.png", "error-distribution.png"]
BADGES = {"overview.png": [ORA, DER, REF], "binocular-pair.png": [ORA, DER], "tangent-geometry.png": [DER],
          "natural-disparity.png": [DER], "natural-validity.png": [DER], "natural-range.png": [DER],
          "measured-point-cloud.png": [DER], "reference-error.png": [REF, DER], "reference-composition.png": [REF],
          "error-distribution.png": [REF]}
# single-hue sequential ramps (light -> dark) and one diverging pair with a neutral midpoint (Visual Language 1 hues)
RANGE_RAMP = (np.array([214, 229, 247.]), np.array([8, 48, 107.]))
DISP_RAMP = (np.array([253, 236, 210.]), np.array([140, 45, 4.]))
ERR_RAMP = (np.array([239, 230, 240.]), np.array([96, 22, 92.]))
DIV_NEG, DIV_MID, DIV_POS = np.array(S.OI_BLUE, float), np.array([236, 235, 232.]), np.array(S.OI_VERM, float)
EMPTY = (247, 246, 242)
PASS_INK = (70, 70, 70)


def sha256(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def fmt(x, nd=3, unit="") -> str:
    return "—" if x is None else f"{x:.{nd}f}{unit}"


class Data:
    def __init__(self, run: Path):
        self.run = run
        j = lambda p: json.loads((run / p).read_text())  # noqa: E731
        self.c = j("acquisition/calibration.json")
        self.acq = j("acquisition/acquisition.json")
        self.pre = j("prelook/prelook-geometry.json")
        self.summ = j("measurement/stereo-summary.json")
        self.ev = j("evaluation/evaluation-summary.json")
        with np.load(run / "acquisition/rgb-observation.npz") as z:
            self.rgb = {k: np.asarray(z[k]) for k in SP.RGB_KEYS}
        with np.load(run / "measurement/stereo-result.npz") as z:
            self.nat = {k: np.asarray(z[k]) for k in z.files}
        with np.load(run / "evaluation/oracle-reference.npz") as z:
            self.orc = {k: np.asarray(z[k]) for k in z.files}
        with np.load(COARSE_RGB[0]) as z:
            self.coarse = np.asarray(z["srgb8"])
        self.sources = {n: sha256(run / n) for n in (
            "acquisition/calibration.json", "acquisition/acquisition.json", "acquisition/rgb-observation.npz",
            "prelook/prelook-geometry.json", "measurement/stereo-result.npz", "measurement/stereo-summary.json",
            "evaluation/evaluation-summary.json", "evaluation/oracle-reference.npz")}
        self.sources[str(COARSE_RGB[0])] = sha256(COARSE_RGB[0])
        self.valid = self.nat["valid"].astype(bool)
        self.n_valid = int(self.valid.sum())
        self.yaw, self.pitch = self.c["gaze_yaw_pitch_deg"]
        self.eL = self.pre["eyes"]["L"]


# ------------------------------------------------------------------ drawing helpers
def ramp(t, ends) -> np.ndarray:
    t = np.clip(np.asarray(t, np.float64), 0, 1)[..., None]
    return np.rint(ends[0] * (1 - t) + ends[1] * t).astype(np.uint8)


def diverging(t) -> np.ndarray:
    """t in [-1, 1]: blue (negative) - neutral gray - vermilion (positive)."""
    t = np.clip(np.asarray(t, np.float64), -1, 1)[..., None]
    neg = DIV_MID * (1 + t) + DIV_NEG * (-t)
    pos = DIV_MID * (1 - t) + DIV_POS * t
    return np.rint(np.where(t < 0, neg, pos)).astype(np.uint8)


def nearest(a: np.ndarray, size: int) -> Image.Image:
    return Image.fromarray(a).resize((size, size), Image.NEAREST)


def box_down(a: np.ndarray, size: int) -> Image.Image:
    return Image.fromarray(a).resize((size, size), Image.BOX)


def frame(dr, x, y, w, h, color=S.INK2, width=1) -> None:
    dr.rectangle([x - 1, y - 1, x + w, y + h], outline=color, width=width)


def caption(dr, x, y, s, size=SMALL, bold=False, fill=S.INK, anchor="la"):
    return S.text(dr, (x, y), s, size=size, bold=bold, fill=fill, outline=None, anchor=anchor)


def statement(img, x, y, w, h, lines, hatch=True) -> None:
    """An explicit empty-result tile: hatched surface with a centred statement."""
    dr = ImageDraw.Draw(img)
    dr.rectangle([x, y, x + w - 1, y + h - 1], fill=EMPTY)
    if hatch:
        S.hatch(img, [x, y, x + w, y + h], (226, 224, 218), spacing=12, width=1)
        dr = ImageDraw.Draw(img)
    frame(dr, x, y, w, h)
    y0 = y + h / 2 - 15 * len(lines)
    for k, ln in enumerate(lines):
        S.text(dr, (x + w / 2, y0 + 30 * k), ln, size=SMALL + (2 if k == 0 else 0), bold=k == 0, fill=S.INK,
               plate=EMPTY, anchor="mm")


def colorbar(img, x, y, w, h, lo, hi, ends=None, div=False, label="", nd=2) -> None:
    dr = ImageDraw.Draw(img)
    t = np.linspace(0, 1, w)[None, :].repeat(h, 0)
    bar = diverging(2 * t - 1) if div else ramp(t, ends)
    img.paste(Image.fromarray(bar), (int(x), int(y)))
    frame(dr, x, y, w, h)
    caption(dr, x, y + h + 4, f"{lo:.{nd}f}", fill=S.INK2)
    caption(dr, x + w, y + h + 4, f"{hi:.{nd}f}", fill=S.INK2, anchor="ra")
    if div:
        caption(dr, x + w / 2, y + h + 4, "0", fill=S.INK2, anchor="ma")
    caption(dr, x + w / 2, y - 4, label, fill=S.INK2, anchor="md")


def header(img, title, lines, badges) -> None:
    B.header(img, title, lines, badges)


def region(img, x, y, w, h, letter, title, badges) -> None:
    dr = ImageDraw.Draw(img)
    dr.rounded_rectangle([x, y, x + w, y + h], radius=10, outline=S.FAINT, width=2, fill=S.PANEL)
    S.text(dr, (x + 18, y + 14), f"{letter} — {title}", size=S.T_HEAD, bold=True, outline=None)
    xr = x + w - 16
    for b in badges:
        xr = S.badge(img, xr, y + 12, b) - 10


def png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=False, compress_level=6)
    return buf.getvalue()


def gamma(rgb_linear) -> np.ndarray:
    return B.gamma_u8(rgb_linear)


# ------------------------------------------------------------------ geometry helpers
def epipole_px(c: dict, side: int) -> tuple[float, float]:
    """Raw-raster image of the other eye's centre direction (the epipole), from the calibration."""
    eye, other = c["eyes"][side], c["eyes"][1 - side]
    far = np.asarray(other["centre_h_m"], float) + 1e6 * (np.asarray(other["centre_h_m"], float)
                                                          - np.asarray(eye["centre_h_m"], float))
    uv, z = FG.project_h(eye, far[None])
    if z[0] <= 0:   # the epipole lies behind: use the opposite direction
        far = 2 * np.asarray(eye["centre_h_m"], float) - far
        uv, _ = FG.project_h(eye, far[None])
    return float(uv[0, 0]), float(uv[0, 1])


def direction_yaw_pitch(d) -> tuple[float, float]:
    d = np.asarray(d, float)
    return math.degrees(math.atan2(d[0], -d[2])), math.degrees(math.atan2(d[1], math.hypot(d[0], d[2])))


# ------------------------------------------------------------------ panels
def coarse_panel(d: Data, s: float = 2.0) -> tuple[Image.Image, dict]:
    """The accepted coarse spherical RGB (ORACLE INPUT) with the executed gaze and the calibration markers."""
    W, H = int(720 * s), int(360 * s)
    img = Image.fromarray(d.coarse).resize((W, H), Image.NEAREST).convert("RGB")
    dr = ImageDraw.Draw(img)
    gx, gy = B.xy(d.yaw, d.pitch, W, H)
    cy_, cp_ = direction_yaw_pitch(d.eL["rectified_core_centre_direction_h"])
    cx, cyy = B.xy(cy_, cp_, W, H)
    bx, by = B.xy(90.0, 0.0, W, H)
    S.crosshair(dr, gx, gy, r=14, solid=True)
    dr.rectangle([cx - 8, cyy - 8, cx + 8, cyy + 8], outline=S.WHITE, width=5)
    dr.rectangle([cx - 8, cyy - 8, cx + 8, cyy + 8], outline=S.INK, width=2)
    S.xmark(dr, bx, by, r=7, color=S.WHITE, width=5)
    S.xmark(dr, bx, by, r=7, color=S.INK, width=2)
    return img, {"gaze": (gx, gy), "core": (cx, cyy), "baseline": (bx, by), "core_yaw_pitch": (cy_, cp_)}


INSET_YAW, INSET_PITCH = (46.0, 106.0), (-20.0, 30.0)


def coarse_inset(d: Data, w: int) -> Image.Image:
    """Magnified crop of the coarse RGB around gaze #1 (cells of 0.5 deg) with the same three glyphs."""
    c0, c1 = int((INSET_YAW[0] + 180) / 0.5), int((INSET_YAW[1] + 180) / 0.5)
    r0, r1 = int((90 - INSET_PITCH[1]) / 0.5), int((90 - INSET_PITCH[0]) / 0.5)
    crop = d.coarse[r0:r1, c0:c1]
    h = int(round(w * crop.shape[0] / crop.shape[1]))
    img = Image.fromarray(crop).resize((w, h), Image.NEAREST).convert("RGB")
    dr = ImageDraw.Draw(img)
    to = lambda yaw, pitch: ((yaw - INSET_YAW[0]) / (INSET_YAW[1] - INSET_YAW[0]) * w,  # noqa: E731
                             (INSET_PITCH[1] - pitch) / (INSET_PITCH[1] - INSET_PITCH[0]) * h)
    cy_, cp_ = direction_yaw_pitch(d.eL["rectified_core_centre_direction_h"])
    gx, gy = to(d.yaw, d.pitch)
    cx, cyy = to(cy_, cp_)
    bx, by = to(90.0, 0.0)
    S.crosshair(dr, gx, gy, r=14, solid=True)
    dr.rectangle([cx - 9, cyy - 9, cx + 9, cyy + 9], outline=S.WHITE, width=5)
    dr.rectangle([cx - 9, cyy - 9, cx + 9, cyy + 9], outline=S.INK, width=2)
    S.xmark(dr, bx, by, r=8, color=S.WHITE, width=5)
    S.xmark(dr, bx, by, r=8, color=S.INK, width=2)
    S.text(dr, (gx, gy - 30), "gaze #1", size=14, bold=True, plate=S.WHITE, anchor="md")
    S.text(dr, (cx - 4, cyy + 22), "rectified core centre", size=13, plate=S.WHITE, anchor="ra")
    S.text(dr, (bx + 12, by - 16), "baseline +X", size=13, plate=S.WHITE, anchor="ld" if bx < w - 110 else "rd")
    return img


def raw_tangent(d: Data, side: str, size: int) -> Image.Image:
    """Raw L / R padded tangent RGB (ORACLE INPUT) with calibration-only markers (DERIVED)."""
    w = d.c["image_size_wh"][0]
    k = size / w
    img = box_down(gamma(d.rgb["rgb_" + side]), size).convert("RGB")
    dr = ImageDraw.Draw(img)
    core = d.c["core_size"]
    o = (w - core) / 2 * k
    S.dashed_rect(dr, [o, o, o + core * k, o + core * k], S.WHITE, width=4, dash=10, gap=6)
    S.dashed_rect(dr, [o, o, o + core * k, o + core * k], S.INK, width=2, dash=10, gap=6)
    S.crosshair(dr, (w - 1) / 2 * k, (w - 1) / 2 * k, r=10, solid=True, width=2)
    src = d.pre["eyes"][side]["raw_source_of_rectified_core_px"]
    x0, x1, y0, y1 = src["x"][0] * k, src["x"][1] * k, src["y"][0] * k, src["y"][1] * k
    pad = 5
    dr.rectangle([x0 - pad, y0 - pad, x1 + pad, y1 + pad], outline=S.WHITE, width=5)
    dr.rectangle([x0 - pad, y0 - pad, x1 + pad, y1 + pad], outline=S.INK, width=2)
    S.text(dr, (x0 - pad - 4, y1 + pad + 6), "rectified-core source", size=max(12, size // 40), plate=S.WHITE, anchor="ra")
    ex, ey = epipole_px(d.c, 0 if side == "L" else 1)
    ex, ey = ex * k, ey * k
    if 0 <= ex <= size and 0 <= ey <= size:
        S.xmark(dr, ex, ey, r=7, color=S.WHITE, width=5)
        S.xmark(dr, ex, ey, r=7, color=S.INK, width=2)
    return img


def hatch_mask(img, x, y, size, mask: np.ndarray) -> None:
    """Hatch the (nearest-resized) core cells of ``mask``: the non-color cue for 'no geometry'."""
    if not mask.any():
        return
    m = Image.fromarray(mask.astype(np.uint8) * 255).resize((size, size), Image.NEAREST)
    full = Image.new("L", img.size, 0)
    full.paste(m, (x, y))
    S.hatch(img, [x, y, x + size, y + size], (190, 186, 176), spacing=10, width=1, mask=full)


def core_image(a: np.ndarray, size: int) -> Image.Image:
    return nearest(a, size)


def valid_or_empty(img, x, y, size, d: Data, layer: np.ndarray | None, empty_lines: list[str]) -> None:
    if layer is None:
        statement(img, x, y, size, size, empty_lines)
    else:
        img.paste(core_image(layer, size), (x, y))
        frame(ImageDraw.Draw(img), x, y, size, size)


def disparity_layer(d: Data, mask: np.ndarray, which: str = "disparity_px") -> tuple[np.ndarray | None, tuple]:
    if not mask.any():
        return None, (0.0, 0.0)
    v = d.nat[which][mask]
    lo, hi = float(np.floor(v.min())), float(np.ceil(v.max()))
    hi = max(hi, lo + 1.0)
    out = np.zeros(mask.shape + (3,), np.uint8)
    out[:] = EMPTY
    out[mask] = ramp((d.nat[which][mask] - lo) / (hi - lo), DISP_RAMP)
    return out, (lo, hi)


def range_layer(d: Data) -> tuple[np.ndarray | None, tuple]:
    if not d.n_valid:
        return None, (0.0, 0.0)
    r = d.nat["range_left_m"][d.valid].astype(np.float64)
    lo, hi = float(r.min()), float(r.max())
    hi = max(hi, lo * 1.01 + 1e-6)
    out = np.zeros(d.valid.shape + (3,), np.uint8)
    out[:] = EMPTY
    out[d.valid] = ramp((np.log(r) - math.log(lo)) / (math.log(hi) - math.log(lo)), RANGE_RAMP)
    return out, (lo, hi)


def mask_layer(m: np.ndarray, on=PASS_INK, off=(255, 255, 255)) -> np.ndarray:
    out = np.zeros(m.shape + (3,), np.uint8)
    out[:] = off
    out[m] = on
    return out


def point_cloud(img, x, y, w, h, d: Data, view: str = "top", title: str = "") -> None:
    sub = Image.new("RGB", (int(w), int(h)), S.WHITE)
    _point_cloud(sub, 0, 0, int(w), int(h), d, view)
    img.paste(sub, (int(x), int(y)))
    if title:
        caption(ImageDraw.Draw(img), x, y - 26, title, bold=True)


def _point_cloud(img, x, y, w, h, d: Data, view: str = "top") -> None:
    """Orthographic projection of the measured points (RGB-coloured), the two eyes, the gaze ray and the core-centre
    ray.  top: head X right / -Z up;  side: along the gaze, -Z right / Y up."""
    dr = ImageDraw.Draw(img)
    dr.rectangle([x, y, x + w - 1, y + h - 1], fill=S.WHITE)
    frame(dr, x, y, w, h)
    g = np.asarray(FG.gaze_direction(d.yaw, d.pitch))
    cdir = np.asarray(d.eL["rectified_core_centre_direction_h"])
    pts = d.nat["xyz_h"][d.valid].astype(np.float64)
    col = gamma(d.nat["rgb_left"][d.valid]) if d.n_valid else np.zeros((0, 3), np.uint8)
    reach = 5.0 if not len(pts) else float(max(5.0, np.quantile(np.linalg.norm(pts, axis=1), 0.99) * 1.1))
    if view == "top":
        P = lambda q: np.stack([q[..., 0], -q[..., 2]], -1)  # noqa: E731
        axes_lbl = ("head X (right) [m]", "head −Z (forward) [m]")
    else:
        P = lambda q: np.stack([-q[..., 2], q[..., 1]], -1)  # noqa: E731
        axes_lbl = ("head −Z (forward) [m]", "head Y (up) [m]")
    anchor = np.array([[0, 0, 0], g * reach, cdir * reach])
    q = np.concatenate([P(anchor), P(pts)]) if len(pts) else P(anchor)
    lo, hi = q.min(0), q.max(0)
    span = float(max(hi - lo)) * 1.08 + 1e-6
    mid = (lo + hi) / 2
    pad = 34

    def to_px(v):
        v = (np.asarray(v) - mid) / span
        return x + pad + (v[..., 0] + 0.5) * (w - 2 * pad), y + h - pad - (v[..., 1] + 0.5) * (h - 2 * pad)
    for k in range(-20, 21):   # recessive 1 m grid
        for axis in (0, 1):
            if axis == 0:
                a, b = to_px(np.array([k, lo[1] - span]))
                c_, d_ = to_px(np.array([k, hi[1] + span]))
            else:
                a, b = to_px(np.array([lo[0] - span, k]))
                c_, d_ = to_px(np.array([hi[0] + span, k]))
            dr.line([float(a), float(b), float(c_), float(d_)], fill=S.GRID, width=1)
    dr.rectangle([x, y, x + w - 1, y + h - 1], outline=S.INK2)
    o = to_px(P(np.zeros(3)))
    for vec, dashed, lbl in ((g, False, "gaze #1"), (cdir, True, "rectified core centre")):
        e = to_px(P(vec * reach))
        if dashed:
            S.dashed_line(dr, [(float(o[0]), float(o[1])), (float(e[0]), float(e[1]))], S.INK, width=2, dash=8, gap=6)
        else:
            dr.line([float(o[0]), float(o[1]), float(e[0]), float(e[1])], fill=S.INK, width=2)
        S.text(dr, (float(e[0]), float(e[1])), lbl, size=14, fill=S.INK, plate=S.WHITE,
               anchor="rb" if e[0] > x + w / 2 else "lb")
    if len(pts):
        px, py = to_px(P(pts))
        order = np.argsort(-pts[:, 1] if view == "top" else pts[:, 0], kind="stable")
        for i in order:
            dr.rectangle([px[i] - 1, py[i] - 1, px[i] + 1, py[i] + 1], fill=tuple(int(v) for v in col[i]))
    else:
        S.text(dr, (x + w / 2, y + h / 2), "0 measured points", size=SMALL + 2, bold=True, plate=S.WHITE, anchor="mm")
    S.text(dr, (float(o[0]), float(o[1])), "eyes", size=13, fill=S.INK2, plate=S.WHITE, anchor="mt")
    dr.ellipse([float(o[0]) - 4, float(o[1]) - 4, float(o[0]) + 4, float(o[1]) + 4], fill=S.INK)
    caption(dr, x + w / 2, y + h - 6, axes_lbl[0], size=13, fill=S.INK2, anchor="md")
    caption(dr, x + 6, y + 6, axes_lbl[1] + "; 1 m grid", size=13, fill=S.INK2)


def histogram(img, x, y, w, h, values_list, edges, labels, colors, xlabel, vlines=()) -> None:
    """Thin-bar histogram; one or two series (the second drawn hatched over the first); legend when > 1 series."""
    dr = ImageDraw.Draw(img)
    dr.rectangle([x, y, x + w, y + h], fill=S.WHITE)
    counts = [np.histogram(v, bins=edges)[0] if len(v) else np.zeros(len(edges) - 1, int) for v in values_list]
    top = max(1, max(int(cn.max()) for cn in counts))
    pad_l, pad_b = 60, 40
    px0, py0, pw, ph = x + pad_l, y + 10, w - pad_l - 14, h - pad_b - 10
    for k in range(5):
        yy = py0 + ph - ph * k / 4
        dr.line([px0, yy, px0 + pw, yy], fill=S.GRID, width=1)
        caption(dr, px0 - 6, yy, f"{int(round(top * k / 4))}", size=13, fill=S.INK2, anchor="rm")
    nb = len(edges) - 1
    bw = pw / nb
    for si, (cn, colr) in enumerate(zip(counts, colors)):
        for b in range(nb):
            if cn[b] <= 0:
                continue
            hh = ph * cn[b] / top
            x0b = px0 + b * bw + 1
            dr.rectangle([x0b, py0 + ph - hh, x0b + max(1.0, bw - 2), py0 + ph], fill=colr)
    dr.line([px0, py0 + ph, px0 + pw, py0 + ph], fill=S.INK2, width=1)
    for t in np.linspace(edges[0], edges[-1], 5):
        xx = px0 + pw * (t - edges[0]) / (edges[-1] - edges[0])
        caption(dr, xx, py0 + ph + 4, f"{t:g}", size=13, fill=S.INK2, anchor="ma")
    for v in vlines:
        xx = px0 + pw * (v - edges[0]) / (edges[-1] - edges[0])
        S.dashed_line(dr, [(xx, py0), (xx, py0 + ph)], S.INK2, width=1, dash=5, gap=4)
        caption(dr, xx + 3, py0 + 2, f"{v * 100:g} cm", size=12, fill=S.INK2)
    caption(dr, px0 + pw / 2, y + h - 2, xlabel, size=13, fill=S.INK2, anchor="md")
    if len(values_list) > 1:
        lx = px0 + pw - 10
        for lbl, colr in reversed(list(zip(labels, colors))):
            bb = caption(dr, lx, py0 + 6, lbl, size=13, fill=S.INK, anchor="ra")
            dr.rectangle([bb[0] - 22, bb[1] + 1, bb[0] - 8, bb[3] - 1], fill=colr)
            lx = bb[0] - 34


def attrition_bars(img, x, y, w, h, summ: dict) -> None:
    dr = ImageDraw.Draw(img)
    rows = summ["term_attrition"]
    n = summ["core_pixels"]
    rh = h / (len(rows) + 1)
    lab_w = 230
    bw = w - lab_w - 110
    caption(dr, x, y, "pixels remaining after each validity term (sequential AND)", bold=True)
    for k, r in enumerate(rows):
        yy = y + rh * (k + 1)
        caption(dr, x + lab_w - 8, yy + rh / 2, r["term"].replace("term_", ""), size=14, anchor="rm")
        frac = r["remaining_after"] / n
        dr.rectangle([x + lab_w, yy + 5, x + lab_w + bw, yy + rh - 5], fill=(240, 239, 235))
        if frac > 0:
            dr.rounded_rectangle([x + lab_w, yy + 5, x + lab_w + max(3.0, bw * frac), yy + rh - 5], radius=3,
                                 fill=S.INK2)
        caption(dr, x + lab_w + bw + 8, yy + rh / 2, f"{r['remaining_after']:,}", size=14, anchor="lm")


# ------------------------------------------------------------------ figures
def lines_prelook(d: Data) -> list[str]:
    p, e = d.pre, d.eL
    return [f"gaze #1: yaw {d.yaw:+.2f}°, pitch {d.pitch:+.2f}° (frozen NB1c RGB gaze #1, executed once)",
            f"tangent frame {d.c.get('tangent_frame')}; IPD {d.c['ipd_m'] * 1000:.0f} mm; vergence "
            f"{d.c['prescribed_vergence_distance_m']:.2f} m; z_rect search {d.c['depth_search_z_rect_m']} m",
            f"stereo leverage L = {p['L']:.4f}; transverse baseline B⊥ = {p['B_perp_m'] * 1000:.2f} mm "
            f"(gaze {p['angle_to_baseline_deg']:.2f}° from the baseline)",
            f"rectification turns the left camera {e['rectification_rotation_deg']:.1f}°; the rectified core centre "
            f"lies {e['rectified_core_centre_from_gaze_deg']:.2f}° from the gaze, "
            f"{e['rectified_core_centre_from_baseline_deg']:.2f}° from the baseline",
            f"z_rect window admits ranges {e['range_admitted_at_core_centre_m'][0]:.1f}–"
            f"{e['range_admitted_at_core_centre_m'][1]:.1f} m at the core centre (calibration only)"]


def ev_lines(d: Data) -> list[str]:
    k, ov = d.ev["counts"], d.ev["overlap_errors"]
    e3, ra = ov["error_3d_m"], ov["radial_abs_m"]
    comp = d.ev["composition_of_natural_valid"]
    out = [f"natural valid {k['natural_valid']:,}; reference valid {k['reference_valid']:,}; overlap {k['overlap']:,}",
           f"natural-only {k['natural_only']:,}; reference-only {k['reference_only']:,} (of {k['core_pixels']:,} core px)"]
    if e3:
        fr = ov["fraction_3d_within_m"]
        out += [f"3-D error median {e3['median'] * 100:.2f} cm, p95 {e3['p95'] * 100:.2f} cm, p99 {e3['p99'] * 100:.2f} cm",
                f"|radial| median {ra['median'] * 100:.2f} cm; within 1 / 2.5 / 5 cm: "
                f"{fr['0.010']:.2f} / {fr['0.025']:.2f} / {fr['0.050']:.2f}"]
    else:
        out += ["no overlap pixels: no 3-D or radial error is defined"]
    out += [f"natural-valid composition: catalog {comp['catalog']:,}, O_0 {comp['O_0_noncatalog_geometry']:,}, "
            f"no geometry {comp['no_geometry']:,}"]
    rc = d.ev["reference_composition"]
    out += [f"rectified core in reference terms: catalog {rc['core_left_catalog_pixels']:,}, O_0 "
            f"{rc['core_left_O_0_pixels']:,}, no geometry {k['core_pixels'] - rc['core_left_geometry_pixels']:,}",
            f"camera model: Position within ±0.5 px ({'yes' if d.ev['camera_model']['ok'] else 'NO'}; max "
            f"{max(d.ev['camera_model'][s]['max_abs_residual_px'] or 0 for s in ('L', 'R')):.4f} px)"]
    return out


def tangent_geometry(d: Data) -> Image.Image:
    W, Hh = 2200, 1250
    img = Image.new("RGB", (W, Hh), S.SURFACE)
    header(img, "AB1a — pre-look sensor geometry at frozen NB1c RGB gaze #1 (calibration only)",
           ["Computed from make_calibration + the accepted rectification before acquisition; it vetoes, moves or "
            "tunes nothing."], [DER])
    dr = ImageDraw.Draw(img)
    # (1) top-down schematic, head frame X right / -Z up (directions to scale, eye spacing exaggerated)
    x0, y0, s = 60, 160, 900
    dr.rectangle([x0, y0, x0 + s, y0 + s], fill=S.WHITE, outline=S.INK2)
    caption(dr, x0, y0 - 30, "top view of the fixed head (X right, −Z forward); eye spacing not to scale", bold=True)
    o = np.array([x0 + 150, y0 + s - 260], float)
    R = 640
    ang = lambda yaw: np.array([math.sin(math.radians(yaw)), -math.cos(math.radians(yaw))])  # noqa: E731
    sep = 70
    eL, eR = o + np.array([-sep, 0]), o + np.array([sep, 0])
    cyaw, _ = direction_yaw_pitch(d.eL["rectified_core_centre_direction_h"])
    for yaw, dash, lbl, anc, off in ((0.0, True, "forward look (L = 1)", "lt", (8, 40)),
                                     (d.yaw, False, f"gaze #1, yaw {d.yaw:+.2f}°", "rb", (0, -8)),
                                     (cyaw, True, f"rectified core centre, yaw {cyaw:+.2f}°", "rb", (0, -10)),
                                     (90.0, False, "baseline +X (epipole direction)", "rt", (0, 10))):
        e = o + ang(yaw) * (R if yaw else R - 60)
        if dash:
            S.dashed_line(dr, [tuple(o), tuple(e)], S.MUTED if yaw == 0 else S.INK, width=2, dash=10, gap=7)
        else:
            dr.line([*o, *e], fill=S.INK if yaw != 90 else S.MUTED, width=3 if yaw == d.yaw else 1)
        S.text(dr, (e[0] + off[0], e[1] + off[1]), lbl, size=14, fill=S.INK, plate=S.WHITE, anchor=anc)
    dr.line([*eL, *eR], fill=S.INK, width=3)
    for e, nm in ((eL, "L"), (eR, "R")):
        dr.ellipse([e[0] - 12, e[1] - 12, e[0] + 12, e[1] + 12], outline=S.INK, width=3, fill=S.WHITE)
        S.text(dr, (e[0], e[1] + 18), nm, size=SMALL, bold=True, outline=None, anchor="ma")
    S.text(dr, (o[0], eL[1] + 46), "baseline b (IPD 63 mm)", size=14, fill=S.INK2, outline=None, anchor="ma")
    # B_perp: the right eye's distance from the gaze line through the left eye (top-view schematic)
    g2 = ang(d.yaw)
    foot = eL + ((eR - eL) @ g2) * g2
    S.dashed_line(dr, [tuple(eL), tuple(eL + g2 * 260)], S.MUTED, width=1, dash=5, gap=4)
    dr.line([*eR, *foot], fill=S.OI_VERM, width=4)
    mid = (eR + foot) / 2
    lab = np.array([x0 + 40, eL[1] - 170])
    dr.line([*mid, *(lab + [60, 6])], fill=S.OI_VERM, width=1)
    S.text(dr, tuple(lab), f"B⊥ = IPD · L = {d.pre['B_perp_m'] * 1000:.2f} mm (schematic)",
           size=15, bold=True, fill=S.INK, plate=S.WHITE, anchor="lb")
    S.text(dr, (x0 + 20, y0 + s - 30), f"L = sqrt(1 − (b·d)²) = {d.pre['L']:.4f}; b·d = {d.pre['b_dot_d']:.4f}",
           size=SMALL, fill=S.INK, outline=None)
    # (2) the left raw tangent raster: nominal core, epipole and the raw source of the rectified core
    rx, ry, rs = 1060, 160, 560
    w = d.c["image_size_wh"][0]
    k = rs / w
    dr.rectangle([rx, ry, rx + rs, ry + rs], fill=S.WHITE, outline=S.INK2)
    caption(dr, rx, ry - 30, "left raw tangent raster (640 × 640 px, 29.4°)", bold=True)
    core = d.c["core_size"]
    oc = (w - core) / 2 * k
    S.dashed_rect(dr, [rx + oc, ry + oc, rx + oc + core * k, ry + oc + core * k], S.INK, width=2)
    S.text(dr, (rx + oc + 4, ry + oc + 4), "nominal 12° core", size=14, fill=S.INK2, plate=S.WHITE)
    S.crosshair(dr, rx + (w - 1) / 2 * k, ry + (w - 1) / 2 * k, r=9, solid=True, width=2)
    src = d.eL["raw_source_of_rectified_core_px"]
    bx0, bx1, by0, by1 = (rx + src["x"][0] * k, rx + src["x"][1] * k, ry + src["y"][0] * k, ry + src["y"][1] * k)
    dr.rectangle([bx0 - 3, by0 - 3, bx1 + 3, by1 + 3], fill=S.INK)
    ex, ey = epipole_px(d.c, 0)
    S.text(dr, (rx + rs - 6, ry + rs - 8), f"epipole at raw x = {ex:.0f}, y = {ey:.0f}"
           + (" (outside the raster)" if not 0 <= ex < w else ""), size=14, fill=S.INK2, plate=S.WHITE, anchor="rd")
    S.text(dr, (bx1 + 3, by1 + 14), "raw source of the whole rectified core", size=14, bold=True, plate=S.WHITE,
           anchor="ra")
    # (3) magnified inset around the source sliver: raw pixel grid
    ix, iy, isz, npx = 1660, 160, 480, 12
    cxp, cyp = int(round(np.mean(src["x"]))), int(round(np.mean(src["y"])))
    xs0, ys0 = cxp - npx // 2, cyp - npx // 2
    crop = gamma(d.rgb["rgb_L"][max(0, ys0):ys0 + npx, max(0, xs0):xs0 + npx])
    tile = np.zeros((npx, npx, 3), np.uint8)
    tile[:] = EMPTY
    tile[max(0, -ys0):max(0, -ys0) + crop.shape[0], max(0, -xs0):max(0, -xs0) + crop.shape[1]] = crop
    img.paste(nearest(tile, isz), (ix, iy))
    dr = ImageDraw.Draw(img)
    q = isz / npx
    for t in range(npx + 1):
        dr.line([ix + t * q, iy, ix + t * q, iy + isz], fill=(255, 255, 255), width=1)
        dr.line([ix, iy + t * q, ix + isz, iy + t * q], fill=(255, 255, 255), width=1)
    sx0, sx1 = ix + (src["x"][0] - xs0 + 0.5) * q, ix + (src["x"][1] - xs0 + 0.5) * q
    sy0, sy1 = iy + (src["y"][0] - ys0 + 0.5) * q, iy + (src["y"][1] - ys0 + 0.5) * q
    dr.rectangle([sx0 - 2, sy0, sx1 + 2, sy1], outline=S.WHITE, width=5)
    dr.rectangle([sx0 - 2, sy0, sx1 + 2, sy1], outline=S.INK, width=2)
    caption(dr, ix, iy - 30, f"raw pixels {xs0}–{xs0 + npx - 1} × {ys0}–{ys0 + npx - 1} (ORACLE INPUT RGB)", bold=True)
    caption(dr, ix, iy + isz + 8, f"box: x {src['x'][0]:.2f}–{src['x'][1]:.2f}, y {src['y'][0]:.2f}–{src['y'][1]:.2f}:",
            size=15)
    caption(dr, ix, iy + isz + 30, "the 256 × 256 rectified core is resampled from this sliver", size=15)
    # (4) numbers
    ty = 800
    for kq, ln in enumerate(lines_prelook(d) + [
            f"rectified principal point c_x = {d.eL['rectified_principal_point_px'][0]:,.1f} px (raster width 640); "
            f"{d.pre['num_disparities']} disparity levels",
            f"rectified-core pixels sourced from the nominal raw core: {d.eL['rectified_core_pixels_from_nominal_raw_core']}"
            f" / {d.pre['core_pixels']:,}; calibration support in the core {d.eL['calibration_support_in_core']:,}"]):
        caption(dr, 1060, ty + 34 * kq, ln, size=SMALL)
    return img


def binocular_pair(d: Data) -> Image.Image:
    W, Hh = 2200, 1260
    img = Image.new("RGB", (W, Hh), S.SURFACE)
    header(img, "AB1a — the one binocular RGB observation (natural sensor data)",
           ["Raw L / R padded tangent images (ORACLE INPUT, display gamma 1/2.2) with calibration-only markers; below, "
            "the rectified 256 × 256 cores the matcher sees.  No truth overlays."], [ORA, DER])
    dr = ImageDraw.Draw(img)
    size = 560
    for i, side in enumerate(("L", "R")):
        x = 60 + i * (size + 60)
        img.paste(raw_tangent(d, side, size), (x, 150))
        dr = ImageDraw.Draw(img)
        frame(dr, x, 150, size, size)
        caption(dr, x, 150 + size + 8, f"raw {side} ({d.acq['render_seconds_lr'][side]:.2f} s, "
                                       f"{d.acq['spp']} spp, seed {d.acq['render_seeds_lr'][side]})", size=15)
    for i, (side, key) in enumerate((("L", "rgb_left"), ("R", "rgb_right"))):
        x = 1320 + i * 420
        img.paste(nearest(gamma(d.nat[key]), 384), (x, 150))
        dr = ImageDraw.Draw(img)
        frame(dr, x, 150, 384, 384)
        caption(dr, x, 150 + 392, f"rectified {side} core (256 × 256, ×1.5)", size=15)
    src = d.eL["raw_source_of_rectified_core_px"]
    for kq, ln in enumerate([
            "Markers (DERIVED, calibration only):",
            "  dashed square: nominal 12° raw core;  crosshair: gaze #1;",
            "  small solid box: raw source of the rectified core",
            f"  (L: x {src['x'][0]:.2f}–{src['x'][1]:.2f}, y {src['y'][0]:.1f}–{src['y'][1]:.1f});",
            "  x: the epipole, when inside the raster.",
            f"Each rectified core resamples {src['x'][1] - src['x'][0]:.2f} × {src['y'][1] - src['y'][0]:.2f} raw px",
            "near the epipole side, not the fixated centre."]):
        caption(dr, 1320, 600 + 30 * kq, ln, size=SMALL, bold=kq == 0)
    caption(dr, 60, 150 + size + 50, f"acquisition: {d.acq['device']}, {d.acq['spp']} spp, BOX filter, no denoising; "
                                     f"passes {', '.join(SP.PASSES)} (truth passes evaluation-only); action source: "
                                     f"{SP.ACTION_SOURCE}", size=15)
    return img


def natural_disparity(d: Data) -> Image.Image:
    W, Hh = 2000, 900
    img = Image.new("RGB", (W, Hh), S.SURFACE)
    sg = d.nat["term_sgbm_left"].astype(bool)
    header(img, "AB1a — natural disparity (RGB only)",
           [f"SGBM-valid core pixels {int(sg.sum()):,}; natural-valid {d.n_valid:,} of {d.valid.size:,}; disparity search "
            f"{int(d.nat['num_disparities'])} levels"], [DER])
    size = 512
    lay, (lo, hi) = disparity_layer(d, sg, "disparity_sgbm_px")
    valid_or_empty(img, 60, 160, size, d, lay, ["0 SGBM-valid pixels"])
    caption(ImageDraw.Draw(img), 60, 160 + size + 8, "SGBM disparity before the gates (all SGBM-valid pixels)", size=15)
    if lay is not None:
        colorbar(img, 60, 160 + size + 60, size, 14, lo, hi, DISP_RAMP, label="disparity [px]", nd=1)
    lay2, (lo2, hi2) = disparity_layer(d, d.valid)
    valid_or_empty(img, 640, 160, size, d, lay2, ["0 natural-valid pixels", "no natural disparity survives the gates"])
    caption(ImageDraw.Draw(img), 640, 160 + size + 8, "refined disparity on natural-valid pixels", size=15)
    if lay2 is not None:
        colorbar(img, 640, 160 + size + 60, size, 14, lo2, hi2, DISP_RAMP, label="disparity [px]", nd=1)
    nd = int(d.nat["num_disparities"])
    edges = np.arange(0, nd + 1, 2, dtype=float)
    histogram(img, 1220, 160, 720, 420, [d.nat["disparity_sgbm_px"][sg], d.nat["disparity_px"][d.valid]], edges,
              ["SGBM-valid", "natural-valid"], [S.FAINT, S.INK2], "disparity [px] (2-px bins)")
    dmax = d.pre["max_disparity_for_z_rect_min_px"]
    caption(ImageDraw.Draw(img), 1220, 600, f"z_rect ≥ 0.75 m ⇔ disparity ≤ {dmax:.1f} px; z_rect ≤ 4.5 m ⇔ "
                                           f"disparity ≥ {dmax * 0.75 / 4.5:.1f} px", size=15)
    return img


def natural_validity(d: Data) -> Image.Image:
    W, Hh = 2000, 1000
    img = Image.new("RGB", (W, Hh), S.SURFACE)
    header(img, "AB1a — natural validity (calibration support only; no identity guard)",
           [f"valid = AND of nine terms; natural-valid {d.n_valid:,} / {d.valid.size:,}"], [DER])
    dr = ImageDraw.Draw(img)
    big = 440
    if d.n_valid:
        img.paste(nearest(mask_layer(d.valid), big), (60, 160))
    else:
        statement(img, 60, 160, big, big, ["0 natural-valid pixels", f"all {d.valid.size:,} invalid"], hatch=False)
    dr = ImageDraw.Draw(img)
    frame(dr, 60, 160, big, big)
    caption(dr, 60, 160 + big + 8, f"natural-valid mask ({d.n_valid:,} px, dark)", size=15)
    t = 170
    for kq, name in enumerate(SP.TERMS):
        x = 560 + (kq % 5) * (t + 26)
        y = 160 + (kq // 5) * (t + 52)
        img.paste(nearest(mask_layer(d.nat[name].astype(bool)), t), (x, y))
        dr = ImageDraw.Draw(img)
        frame(dr, x, y, t, t)
        caption(dr, x, y + t + 4, f"{name.replace('term_', '')}: {int(d.nat[name].sum()):,}", size=13)
    attrition_bars(img, 560, 620, 1380, 340, d.summ)
    return img


def natural_range(d: Data) -> Image.Image:
    W, Hh = 1700, 860
    img = Image.new("RGB", (W, Hh), S.SURFACE)
    r = d.summ["range_left_m_valid"]
    header(img, "AB1a — natural range from the left eye (RGB stereo, natural-valid pixels)",
           [f"natural-valid {d.n_valid:,}; range median {fmt(r and r['median'], 3, ' m')}, min {fmt(r and r['min'], 3)}, "
            f"max {fmt(r and r['max'], 3)} m"], [DER])
    size = 512
    lay, (lo, hi) = range_layer(d)
    adm = d.eL["range_admitted_at_core_centre_m"]
    valid_or_empty(img, 60, 160, size, d, lay, ["0 natural-valid pixels", "no natural range",
                                                f"(z_rect admits {adm[0]:.1f}–{adm[1]:.1f} m at the core centre)"])
    if lay is not None:
        colorbar(img, 60, 160 + size + 40, size, 14, lo, hi, RANGE_RAMP, label="range [m] (log scale)")
    v = d.nat["range_left_m"][d.valid]
    if len(v):
        e = np.linspace(float(np.floor(v.min())), float(np.ceil(v.max())) + 1e-9, 41)
    else:
        e = np.linspace(0, 10, 41)
    histogram(img, 640, 160, 1000, 420, [v], e, ["natural-valid"], [S.INK2], "range from the left eye [m]")
    return img


def measured_point_cloud(d: Data) -> Image.Image:
    W, Hh = 1700, 880
    img = Image.new("RGB", (W, Hh), S.SURFACE)
    bb = d.summ["xyz_h_bbox_valid_m"]
    header(img, "AB1a — measured local point cloud (natural RGB stereo; head frame; RGB-coloured)",
           [f"{d.n_valid:,} points" + (f"; extent {', '.join(f'{x:.3f}' for x in bb['extent'])} m (X, Y, Z)" if bb else
                                       "; nothing was measured")], [DER])
    point_cloud(img, 60, 190, 780, 640, d, "top", "top view")
    point_cloud(img, 880, 190, 780, 640, d, "side", "side view")
    return img


def ref_layers(d: Data) -> dict:
    ids = d.orc["instance_id"]
    geom = d.orc["left_geometry"].astype(bool)
    comp = B.id_palette(ids)
    comp[(ids == 0) & geom] = S.OI_ORANGE
    comp[~geom] = EMPTY
    R, N = d.orc["valid"].astype(bool), d.valid
    cat = np.zeros(R.shape + (3,), np.uint8)
    cat[:] = (255, 255, 255)
    cat[R & ~N] = S.OI_SKY
    cat[N & ~R] = S.OI_VERM
    cat[N & R] = S.INK
    return {"composition": comp, "categories": cat, "nogeom": ~geom}


def reference_error(d: Data) -> Image.Image:
    W, Hh = 2240, 1000
    img = Image.new("RGB", (W, Hh), S.SURFACE)
    header(img, "AB1a — post-freeze reference / evaluation (Classroom-Oracle-1 local oracle, same calibration and gaze)",
           ["Evaluation only: Blender Position + Object Index + same-instance right-eye visibility.  Opened after the "
            "measurement freeze; changes nothing in the natural measurement."], [REF, DER])
    lay = ref_layers(d)
    size = 440
    img.paste(nearest(lay["composition"], size), (60, 160))
    hatch_mask(img, 60, 160, size, lay["nogeom"])
    if lay["nogeom"].all():
        S.text(ImageDraw.Draw(img), (60 + size / 2, 160 + size / 2), "no geometry in the whole core", size=SMALL,
               bold=True, plate=EMPTY, anchor="mm")
    dr = ImageDraw.Draw(img)
    frame(dr, 60, 160, size, size)
    rc = d.ev["reference_composition"]
    caption(dr, 60, 160 + size + 8, f"left reference at the core: catalog {rc['core_left_catalog_pixels']:,}, O_0 "
                                    f"{rc['core_left_O_0_pixels']:,} (orange)", size=14)
    caption(dr, 60, 160 + size + 28, f"no geometry {d.valid.size - rc['core_left_geometry_pixels']:,} (pale)", size=14)
    if (d.valid | d.orc["valid"].astype(bool)).any():
        img.paste(nearest(lay["categories"], size), (540, 160))
    else:
        statement(img, 540, 160, size, size, ["0 natural-valid, 0 reference-valid", "no support to compare"], hatch=False)
    dr = ImageDraw.Draw(img)
    frame(dr, 540, 160, size, size)
    k = d.ev["counts"]
    for j, (colr, lbl) in enumerate(((S.INK, f"overlap {k['overlap']:,}"), (S.OI_VERM, f"natural-only {k['natural_only']:,}"),
                                     (S.OI_SKY, f"reference-only {k['reference_only']:,}"))):
        dr.rectangle([540, 160 + size + 12 + 24 * j, 556, 160 + size + 28 + 24 * j], fill=colr)
        caption(dr, 564, 160 + size + 10 + 24 * j, lbl, size=14)
    rad = d.orc["radial_signed_m"]
    ov = d.orc["overlap"].astype(bool)
    if ov.any():
        lim = float(max(0.01, np.quantile(np.abs(rad[ov]), 0.99)))
        layer = np.zeros(ov.shape + (3,), np.uint8)
        layer[:] = EMPTY
        layer[ov] = diverging(rad[ov] / lim)
        img.paste(nearest(layer, size), (1020, 160))
        colorbar(img, 1020, 160 + size + 40, size, 14, -lim, lim, div=True, label="signed radial error r_N − r_R [m]")
    else:
        statement(img, 1020, 160, size, size, ["no overlap", "no error is defined"])
    dr = ImageDraw.Draw(img)
    frame(dr, 1020, 160, size, size)
    caption(dr, 1020, 130, "signed radial error on the overlap", bold=True, size=15)
    caption(dr, 60, 130, "reference composition (left)", bold=True, size=15)
    caption(dr, 540, 130, "natural vs reference support", bold=True, size=15)
    for kq, ln in enumerate(ev_lines(d) + [
            f"natural-only reasons: " + ", ".join(f"{a} {b:,}" for a, b in d.ev["natural_only_reasons"].items() if b),
            f"camera model: Position projects within ±{d.ev['camera_model']['tolerance_px']} px "
            f"({'yes' if d.ev['camera_model']['ok'] else 'NO'}; max L {fmt(d.ev['camera_model']['L']['max_abs_residual_px'], 4)} px)"]):
        caption(dr, 1500, 170 + 34 * kq, ln, size=15)
    return img


def reference_composition(d: Data) -> Image.Image:
    W, Hh = 1700, 760
    img = Image.new("RGB", (W, Hh), S.SURFACE)
    comp = d.ev["composition_of_natural_valid"]
    header(img, "AB1a — reference composition (evaluation only)",
           [f"what the rectified core sees in reference terms, and what the natural-valid pixels landed on "
            f"({comp['distinct_catalog_instances']} distinct catalog instances touched)"], [REF])
    dr = ImageDraw.Draw(img)
    rc = d.ev["reference_composition"]
    n = d.valid.size
    rows = [("core: catalog geometry", rc["core_left_catalog_pixels"], n),
            ("core: O_0 noncatalog geometry", rc["core_left_O_0_pixels"], n),
            ("core: no geometry", n - rc["core_left_geometry_pixels"], n),
            ("natural-valid: catalog", comp["catalog"], max(1, comp["natural_valid"])),
            ("natural-valid: O_0", comp["O_0_noncatalog_geometry"], max(1, comp["natural_valid"])),
            ("natural-valid: no geometry", comp["no_geometry"], max(1, comp["natural_valid"]))]
    x, y, bw = 60, 170, 900
    for kq, (lbl, v, tot) in enumerate(rows):
        yy = y + 52 * kq
        caption(dr, x + 330, yy + 16, lbl, size=15, anchor="rm")
        dr.rectangle([x + 340, yy + 4, x + 340 + bw, yy + 30], fill=(240, 239, 235))
        if v:
            dr.rounded_rectangle([x + 340, yy + 4, x + 340 + max(3, bw * v / tot), yy + 30], radius=3, fill=S.INK2)
        caption(dr, x + 350 + bw, yy + 16, f"{v:,} ({100 * v / tot:.1f} %)" if tot else f"{v:,}", size=15, anchor="lm")
    caption(dr, 60, 500, "reference-valid instances (oracle): " + (", ".join(
        f"{e['object_name']} {e['pixels']:,}" for e in d.ev["reference_composition"]["reference_valid_instances"][:6])
        or "none"), size=15)
    caption(dr, 60, 530, "natural-valid catalog instances: " + (", ".join(
        f"{e['object_name']} {e['pixels']:,}" for e in comp["instances"][:6]) or "none"), size=15)
    return img


def error_distribution(d: Data) -> Image.Image:
    W, Hh = 1700, 700
    img = Image.new("RGB", (W, Hh), S.SURFACE)
    header(img, "AB1a — error distributions (post-freeze; descriptive, no pass / fail)",
           ["3-D error on the overlap with the oracle, and against the left first-hit Position for every natural-valid "
            "pixel with geometry"], [REF])
    ov = d.orc["overlap"].astype(bool)
    e_ov = d.orc["error_3d_m"][ov]
    xyz = d.nat["xyz_h"].astype(np.float64)
    fh = d.valid & d.orc["left_geometry"].astype(bool)
    e_fh = np.linalg.norm(xyz - d.orc["left_position_h"].astype(np.float64), axis=-1)[fh]
    top = float(np.quantile(np.concatenate([e_ov, e_fh]), 0.99)) if (len(e_ov) + len(e_fh)) else 0.1
    top = max(0.06, top)
    edges = np.linspace(0, top, 41)
    histogram(img, 60, 160, 1580, 480, [np.clip(e_fh, 0, top), np.clip(e_ov, 0, top)], edges,
              [f"vs left first hit ({len(e_fh):,})", f"overlap vs oracle ({len(e_ov):,})"], [S.FAINT, S.INK2],
              "3-D error [m] (values above the axis end are clipped into the last bin)", vlines=SP.ERROR_FRACTIONS_M)
    return img


def overview(d: Data) -> Image.Image:
    W, Hh = 2400, 2620
    img = Image.new("RGB", (W, Hh), S.SURFACE)
    header(img, "Active Bootstrap-1a — what did the eye measure from one RGB-selected look?",
           [f"One fixation, one binocular pair, RGB-only stereo (no depth, no identity, no Position); measurement frozen "
            f"before any reference truth.  Action source: {SP.ACTION_SOURCE}.  No second gaze, no controller."],
           [ORA, DER, REF])
    # A
    ax, ay, aw, ah = 40, 130, W - 80, 760
    region(img, ax, ay, aw, ah, "A", "FROZEN ACTION / SENSOR GEOMETRY", [DER, ORA])
    pano, pts = coarse_panel(d, 1.75)
    img.paste(pano, (ax + 20, ay + 70))
    dr = ImageDraw.Draw(img)
    frame(dr, ax + 20, ay + 70, pano.size[0], pano.size[1])
    gx, gy = pts["gaze"]
    cx, cy = pts["core"]
    S.text(dr, (ax + 20 + gx - 20, ay + 70 + gy - 22), "gaze #1", size=SMALL, bold=True, plate=S.WHITE, anchor="rd")
    S.text(dr, (ax + 20 + cx + 14, ay + 70 + cy + 18), "rectified core centre", size=14, plate=S.WHITE, anchor="la")
    bx, by = pts["baseline"]
    S.text(dr, (ax + 20 + bx + 12, ay + 70 + by - 14), "baseline +X", size=14, plate=S.WHITE, anchor="ld")
    caption(dr, ax + 20, ay + 70 + pano.size[1] + 8, "coarse spherical RGB (ORACLE INPUT, the NB1c source), yaw −180…180°",
            size=14, fill=S.INK2)
    ins = coarse_inset(d, 460)
    ix = ax + aw - 20 - ins.size[0]
    img.paste(ins, (ix, ay + 70))
    dr = ImageDraw.Draw(img)
    frame(dr, ix, ay + 70, ins.size[0], ins.size[1])
    caption(dr, ix, ay + 70 + ins.size[1] + 6, f"magnified: yaw {INSET_YAW[0]:.0f}…{INSET_YAW[1]:.0f}°, pitch "
                                               f"{INSET_PITCH[0]:.0f}…{INSET_PITCH[1]:.0f}° (0.5° cells)",
            size=13, fill=S.INK2)
    tx = ax + 40 + pano.size[0] + 20
    for kq, ln in enumerate(["frozen NB1c RGB gaze #1", f"yaw {d.yaw:+.2f}°  pitch {d.pitch:+.2f}°",
                             f"tangent frame: {d.c.get('tangent_frame')}", f"IPD {d.c['ipd_m'] * 1000:.0f} mm, vergence "
                             f"{d.c['prescribed_vergence_distance_m']:.2f} m",
                             f"stereo leverage L = {d.pre['L']:.4f}", f"B⊥ = IPD · L = {d.pre['B_perp_m'] * 1000:.2f} mm",
                             f"(a forward look: L = 1, B⊥ = 63 mm)", "",
                             "calibration only (pre-look):",
                             f"rectification turns the camera {d.eL['rectification_rotation_deg']:.1f}°",
                             f"rectified core centre: {d.eL['rectified_core_centre_from_gaze_deg']:.2f}° from the gaze,",
                             f"  {d.eL['rectified_core_centre_from_baseline_deg']:.2f}° from the baseline",
                             f"z_rect admits {d.eL['range_admitted_at_core_centre_m'][0]:.1f}–"
                             f"{d.eL['range_admitted_at_core_centre_m'][1]:.1f} m there"]):
        caption(dr, tx, ay + 80 + 34 * kq, ln, size=SMALL + (2 if kq < 2 else 0), bold=kq in (0, 8))
    # B
    by0 = ay + ah + 30
    bh = 570
    region(img, ax, by0, aw, bh, "B", "NATURAL SENSOR DATA (rendered binocular RGB)", [ORA, DER])
    s = 440
    for i, side in enumerate(("L", "R")):
        x = ax + 20 + i * (s + 30)
        img.paste(raw_tangent(d, side, s), (x, by0 + 70))
        frame(ImageDraw.Draw(img), x, by0 + 70, s, s)
        caption(ImageDraw.Draw(img), x, by0 + 70 + s + 4, f"raw {side} tangent (dashed: 12° core; box: rectified-core source)",
                size=13, fill=S.INK2)
    for i, (side, key) in enumerate((("L", "rgb_left"), ("R", "rgb_right"))):
        x = ax + 20 + 2 * (s + 30) + 40 + i * (s + 30)
        img.paste(nearest(gamma(d.nat[key]), s), (x, by0 + 70))
        frame(ImageDraw.Draw(img), x, by0 + 70, s, s)
        caption(ImageDraw.Draw(img), x, by0 + 70 + s + 4, f"rectified {side} core 256 × 256", size=13, fill=S.INK2)
    # C
    cy0 = by0 + bh + 30
    ch = 550
    region(img, ax, cy0, aw, ch, "C", "DERIVED NATURAL MEASUREMENT", [DER])
    s = 420
    x0 = ax + 20
    lay, (lo, hi) = disparity_layer(d, d.valid)
    valid_or_empty(img, x0, cy0 + 70, s, d, lay, ["0 natural-valid pixels", "no disparity"])
    caption(ImageDraw.Draw(img), x0, cy0 + 70 + s + 4, "disparity (natural-valid)" + (f" {lo:.0f}–{hi:.0f} px" if lay is not None else ""), size=13, fill=S.INK2)
    if d.n_valid:
        img.paste(nearest(mask_layer(d.valid), s), (x0 + s + 30, cy0 + 70))
    else:
        statement(img, x0 + s + 30, cy0 + 70, s, s, ["valid mask", f"all {d.valid.size:,} pixels invalid"], hatch=False)
    frame(ImageDraw.Draw(img), x0 + s + 30, cy0 + 70, s, s)
    caption(ImageDraw.Draw(img), x0 + s + 30, cy0 + 70 + s + 4, f"valid mask: {d.n_valid:,} / {d.valid.size:,}", size=13,
            fill=S.INK2)
    lay, (lo, hi) = range_layer(d)
    valid_or_empty(img, x0 + 2 * (s + 30), cy0 + 70, s, d, lay, ["0 natural-valid pixels", "no range"])
    caption(ImageDraw.Draw(img), x0 + 2 * (s + 30), cy0 + 70 + s + 4,
            "range (natural-valid)" + (f" {lo:.2f}–{hi:.2f} m" if lay is not None else ""), size=13, fill=S.INK2)
    point_cloud(img, x0 + 3 * (s + 30), cy0 + 70, W - 80 - 40 - 3 * (s + 30), s, d, "top")
    caption(ImageDraw.Draw(img), x0 + 3 * (s + 30), cy0 + 70 + s + 4, "measured points, top view (RGB-coloured)", size=13,
            fill=S.INK2)
    # D
    dy0 = cy0 + ch + 30
    dh = Hh - dy0 - 30
    region(img, ax, dy0, aw, dh, "D", "REFERENCE / EVALUATION (post-freeze)", [REF])
    lay = ref_layers(d)
    s = 380
    img.paste(nearest(lay["composition"], s), (ax + 20, dy0 + 70))
    hatch_mask(img, ax + 20, dy0 + 70, s, lay["nogeom"])
    if lay["nogeom"].all():
        S.text(ImageDraw.Draw(img), (ax + 20 + s / 2, dy0 + 70 + s / 2), "no geometry in the whole core", size=SMALL,
               bold=True, plate=EMPTY, anchor="mm")
    frame(ImageDraw.Draw(img), ax + 20, dy0 + 70, s, s)
    caption(ImageDraw.Draw(img), ax + 20, dy0 + 70 + s + 4, "reference at the rectified core (Object Index / Position); "
            "hatched: no geometry", size=13, fill=S.INK2)
    ov = d.orc["overlap"].astype(bool)
    if ov.any():
        rad = d.orc["radial_signed_m"]
        lim = float(max(0.01, np.quantile(np.abs(rad[ov]), 0.99)))
        layer = np.zeros(ov.shape + (3,), np.uint8)
        layer[:] = EMPTY
        layer[ov] = diverging(rad[ov] / lim)
        img.paste(nearest(layer, s), (ax + 20 + s + 30, dy0 + 70))
        caption(ImageDraw.Draw(img), ax + 20 + s + 30, dy0 + 70 + s + 4, f"signed radial error, ±{lim * 100:.1f} cm", size=13,
                fill=S.INK2)
    else:
        statement(img, ax + 20 + s + 30, dy0 + 70, s, s, ["no overlap", "no error is defined"])
    frame(ImageDraw.Draw(img), ax + 20 + s + 30, dy0 + 70, s, s)
    dr = ImageDraw.Draw(img)
    for kq, ln in enumerate(ev_lines(d)):
        caption(dr, ax + 20 + 2 * (s + 30) + 10, dy0 + 80 + 36 * kq, ln, size=SMALL)
    return img


def render_all(run: Path) -> dict[str, Image.Image]:
    d = Data(run)
    figs = {"overview.png": overview(d), "binocular-pair.png": binocular_pair(d),
            "tangent-geometry.png": tangent_geometry(d), "natural-disparity.png": natural_disparity(d),
            "natural-validity.png": natural_validity(d), "natural-range.png": natural_range(d),
            "measured-point-cloud.png": measured_point_cloud(d), "reference-error.png": reference_error(d),
            "reference-composition.png": reference_composition(d)}
    if d.orc["overlap"].any() or (d.valid & d.orc["left_geometry"].astype(bool)).any():
        figs["error-distribution.png"] = error_distribution(d)
    return figs, d


def visualize(run: Path, vis: Path) -> dict:
    vis.mkdir(parents=True, exist_ok=True)
    figs, d = render_all(run)
    out = {}
    for name in FIGURES:
        if name in figs:
            (vis / name).write_bytes(png_bytes(figs[name]))
            out[name] = {"sha256": sha256(vis / name), "badges": BADGES[name], "size": list(figs[name].size)}
        else:
            out[name] = {"omitted": "no overlap and no natural-valid pixel with geometry: no error distribution"}
    man = {"schema": "AB1a-visuals-manifest-v1", "figures": out, "sources": d.sources,
           "regenerate": ".venv/bin/python tools/active_bootstrap/ab1a_run.py visualize --run RUN --visuals VIS",
           "style": "Visual Language 1 (tools/visual_language/style.py)", "fonts": S.font_hashes()}
    (vis / "visuals-manifest.json").write_text(json.dumps(man, indent=1, sort_keys=True) + "\n")
    print(f"[ab1a] visualize: {sum('sha256' in v for v in out.values())} figures -> {vis}")
    return man
