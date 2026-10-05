"""Active Bootstrap-1d3: the persistent human-facing figures of the one-shot SGBM viability test.

Contract: docs/active-bootstrap/ab1d3-sgbm-viability-contract.md, section 17.  Reads the AB1d3 run (SGBM records,
adapter records, evaluation) and the accepted AB1d2 4096-spp RGB observations.  Visual Language 1 (``style.py``) and the
accepted AB1b / AB1c figure helpers (read-only).  Invalid / unevaluable pixels are never hidden: they are drawn in the
no-correspondence tone WITH a diagonal hatch.  Display transforms: images are ``fsg_stereo.linear_to_u8`` RGB, no
stretch; error maps use fixed log ramps identical for SGBM and the primitive matcher.  Deterministic: the checker
regenerates every PNG byte-identically.
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
import ab1c_visuals as CV  # noqa: E402  (accepted AB1c figure helpers, read-only)
import ab1d3_spec as SP  # noqa: E402
import fsg_stereo as FS  # noqa: E402  (accepted photometric transfer, read-only)
import style as S  # noqa: E402  (Visual Language 1, read-only)

ORA, DER, REF = SP.TRUTH_ORACLE, SP.TRUTH_DERIVED, SP.TRUTH_REFERENCE
BADGES = {"overview.png": [ORA, DER, REF], "sgbm-vs-primitive.png": [DER, REF], "disparity-validity.png": [ORA, DER],
          "metric-error.png": [DER, REF], "attrition.png": [DER, REF]}
SAME = ("SAME photons as AB1d2 (the accepted 4096-spp observations) · NO new render · NO truth at matcher time · "
        "ONE frozen SGBM configuration, ONE run")
NOT_STATEMENT = ("SGBM is PLANAR internally (rectified 640 × 640); its disparity is mapped back to the RAW correspondence "
                 "product and measured with the accepted AB1b spherical geometry.  No tuning, no sweep, no head motion, "
                 "no controller.")
GAZE_COLORS = [S.OI_BLUE, S.OI_VERM, S.OI_GREEN]
C_PRIM, C_SGBM = S.INK2, S.OI_BLUE
CAT_COLORS = {"both_correct": S.OI_GREEN, "primitive_only": S.OI_ORANGE, "sgbm_only": S.OI_BLUE,
              "neither": (214, 211, 204)}
CAT_NAMES = {"both_correct": "both ≤ 1 px", "primitive_only": "primitive only ≤ 1 px", "sgbm_only": "SGBM only ≤ 1 px",
             "neither": "neither (wrong or no output)"}
LOSS_GROUPS = [("rectifiable", "not rectifiable", (120, 120, 120)),
               ("footprint_term_sgbm_left", "SGBM left invalid", S.OI_VERM),
               ("footprint_term_right_valid", "right / LR / raster", S.OI_ORANGE),
               ("footprint_term_support_left", "support", S.OI_PURPLE),
               ("footprint_term_inside_raster", "right / LR / raster", S.OI_ORANGE),
               ("footprint_term_lr", "right / LR / raster", S.OI_ORANGE),
               ("footprint_term_texture", "texture < 0.5 u8", S.OI_YELLOW),
               ("footprint_term_finite", "z_rect / finite", S.OI_SKY),
               ("footprint_term_z_range", "z_rect / finite", S.OI_SKY),
               ("footprint_term_roi", "disparity ROI", S.OI_PURPLE),
               ("raw_in_front", "raw adapter", S.INK),
               ("raw_inside", "raw adapter", S.INK)]
LOSS_LEGEND = [("SGBM left invalid", S.OI_VERM), ("right / LR / raster", S.OI_ORANGE), ("texture < 0.5 u8", S.OI_YELLOW),
               ("z_rect / finite", S.OI_SKY), ("support / disparity ROI", S.OI_PURPLE), ("not rectifiable", (120, 120, 120)),
               ("raw adapter", S.INK), ("VALID product", (205, 230, 214))]
TERM_COLORS = {"term_sgbm_left": S.OI_VERM, "term_right_valid": S.OI_ORANGE, "term_support_left": S.OI_PURPLE,
               "term_inside_raster": S.OI_ORANGE, "term_lr": S.OI_ORANGE, "term_texture": S.OI_YELLOW,
               "term_finite": S.OI_SKY, "term_z_range": S.OI_SKY, "term_roi": S.OI_PURPLE}
VALID_TONE = (205, 230, 214)
caption, stat_lines, region, header, frame = BV.caption, BV.stat_lines, BV.region, BV.header, BV.frame
png_bytes, diverging, colorbar, ramp = BV.png_bytes, BV.diverging, BV.colorbar, BV.ramp
fmt_len, qv = CV.fmt_len, CV.qv
ERR_RAMP, DISP_RAMP, NOCORR = BV.ERR_RAMP, BV.DISP_RAMP, BV.NOCORR
N = SP.CORE_SIZE


def sha256(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def npz(path: Path) -> dict:
    with np.load(path, allow_pickle=False) as z:
        return {k: np.asarray(z[k]) for k in z.files}


def j(path: Path):
    return json.loads(Path(path).read_text())


class Gaze:
    def __init__(self, run: Path, g: str, k: int, rgb_path: Path):
        self.g, self.k, self.tab = g, k, SP.GAZE_TABLE[g]
        o = npz(rgb_path)
        self.rgb = (o["rgb_L"], o["rgb_R"])
        self.sg = npz(run / f"sgbm/{g}/sgbm-record.npz")
        self.ad = npz(run / f"correspondence/{g}/adapter-record.npz")
        self.ev = npz(run / f"evaluation/{g}/evaluation-result.npz")
        self.ssum = j(run / f"sgbm/{g}/sgbm-summary.json")
        self.asum = j(run / f"correspondence/{g}/adapter-summary.json")
        self.files = [rgb_path] + [run / p for p in (f"sgbm/{g}/sgbm-record.npz", f"correspondence/{g}/adapter-record.npz",
                                                     f"evaluation/{g}/evaluation-result.npz", f"sgbm/{g}/sgbm-summary.json",
                                                     f"correspondence/{g}/adapter-summary.json")]

    def label(self) -> str:
        return f"gaze {self.k + 1}: ({self.tab['yaw_deg']:+.2f}°, {self.tab['pitch_deg']:+.2f}°)"

    def outline(self) -> np.ndarray:
        """The raw left core's boundary in rectified-left coordinates (for drawing on rectified panels)."""
        u = self.ad["uvrect_L"].reshape(N, N, 2)
        return np.concatenate([u[0, :], u[:, -1], u[-1, ::-1], u[::-1, 0]])


class Data:
    def __init__(self, run: Path, rgb_paths: dict | None = None):
        self.run = run
        self.ev = j(run / "evaluation/evaluation-summary.json")
        rp = rgb_paths or {g: SP.rgb_path(g) for g in SP.GAZES}
        self.gz = [Gaze(run, g, k, Path(rp[g])) for k, g in enumerate(SP.GAZES)]
        self.sources = {"evaluation/evaluation-summary.json": sha256(run / "evaluation/evaluation-summary.json")}
        for z in self.gz:
            for p in z.files:
                p = Path(p)
                self.sources[str(p.relative_to(run)) if p.is_relative_to(run) else str(p)] = sha256(p)

    def per(self, z: Gaze) -> dict:
        return self.ev["per_gaze"][z.g]


# ------------------------------------------------------------------ layers (display transforms recorded in the manifest)
def u8(rgb) -> np.ndarray:
    return FS.linear_to_u8(rgb).astype(np.uint8)


def core_view(rgb, size) -> Image.Image:
    o = SP.CORE_ORIGIN
    return Image.fromarray(u8(rgb[o:o + N, o:o + N])).resize((size, size), Image.NEAREST)


def log_layer(values_core: np.ndarray, lo: float, hi: float, ends) -> tuple[np.ndarray, np.ndarray]:
    g = np.asarray(values_core, np.float64).reshape(N, N)
    m = np.isfinite(g)
    out = np.zeros((N, N, 3), np.uint8)
    out[:] = NOCORR
    out[m] = ramp((np.log10(np.maximum(np.abs(g[m]), 10.0 ** lo)) - lo) / (hi - lo), ends)
    return out, ~m


def err_layer(e_px_core) -> tuple[np.ndarray, np.ndarray]:
    return log_layer(e_px_core, -2.0, 2.5, ERR_RAMP)            # 0.01 .. ~300 px


def e3_layer(e3_core) -> tuple[np.ndarray, np.ndarray]:
    return log_layer(e3_core, -4.0, -0.5, ERR_RAMP)             # 0.1 mm .. ~0.3 m (saturates above)


def cat_layer(catmap) -> tuple[np.ndarray, np.ndarray]:
    c = np.asarray(catmap).reshape(N, N)
    out = np.zeros((N, N, 3), np.uint8)
    out[:] = NOCORR
    for k, name in enumerate(SP.CATEGORIES):
        out[c == k] = CAT_COLORS[name]
    return out, c < 0


def loss_layer(ad: dict) -> tuple[np.ndarray, np.ndarray]:
    out = np.zeros((N * N, 3), np.uint8)
    out[:] = VALID_TONE
    lost = np.zeros(N * N, bool)
    prev = np.ones(N * N, bool)
    for stage, _name, col in LOSS_GROUPS:
        s = np.asarray(ad["stage_" + stage], bool)
        here = prev & ~s
        out[here] = col
        lost |= here
        prev = s
    return out.reshape(N, N, 3), np.zeros((N, N), bool)


def disp_layer(sg: dict, size: int) -> tuple[np.ndarray, np.ndarray]:
    d = sg["disparity_px"].astype(np.float64)
    v = sg["valid"].astype(bool)
    out = np.zeros(d.shape + (3,), np.uint8)
    out[:] = NOCORR
    out[v] = ramp((d[v] - 0.0) / float(SP.NUM_DISPARITIES), DISP_RAMP)
    return out, ~v


def first_fail_layer(sg: dict) -> tuple[np.ndarray, np.ndarray]:
    h, w = sg["valid"].shape
    out = np.zeros((h, w, 3), np.uint8)
    out[:] = VALID_TONE
    done = np.zeros((h, w), bool)
    for t in SP.TERMS:
        f = ~np.asarray(sg[t], bool) & ~done
        out[f] = TERM_COLORS[t]
        done |= f
    return out, np.zeros((h, w), bool)


def paste(img, arr, x, y, size, hatch_mask=None) -> None:
    CV.paste_core(img, arr, x, y, size, hatch_mask)


def paste_raster(img, arr, x, y, size, hatch_mask=None, outline=None) -> None:
    """A full 640 x 640 rectified raster scaled to ``size``; optional raw-core outline (rectified coordinates)."""
    CV.paste_core(img, arr, x, y, size, hatch_mask)
    if outline is not None:
        dr = ImageDraw.Draw(img)
        s = size / SP.RAW_SIZE
        pts = [(x + (u + 0.5) * s, y + (v + 0.5) * s) for u, v in outline[::8]]
        S.dashed_line(dr, pts + [pts[0]], S.INK, width=2, dash=6, gap=4)


def gaze_tag(img, x, y, z: Gaze, size=18) -> None:
    dr = ImageDraw.Draw(img)
    S.crosshair(dr, x + 12, y + 13, r=10, solid=True, color=GAZE_COLORS[z.k])
    S.text(dr, (x + 30, y), z.label(), size=size, bold=True, outline=None)


def legend(img, x, y, items, step=290, size=15) -> None:
    dr = ImageDraw.Draw(img)
    for k, (name, col) in enumerate(items):
        xx = x + step * k
        dr.rectangle([xx, y + 3, xx + 18, y + 19], fill=col, outline=S.INK2)
        caption(dr, xx + 26, y, name, size=size)


def hatch_legend(img, x, y, label) -> None:
    dr = ImageDraw.Draw(img)
    dr.rectangle([x, y + 3, x + 18, y + 19], fill=NOCORR, outline=S.INK2)
    S.hatch(img, [x, y + 3, x + 18, y + 19], (196, 192, 184), spacing=6, width=1)
    caption(ImageDraw.Draw(img), x + 26, y, label, size=15)


def f3(v, fmt="{:.3f}") -> str:
    return "—" if v is None else fmt.format(v)


def dashed_poly(dr, pts, fill, width=2, dash=9, gap=6) -> None:
    """A dashed polyline whose dash phase runs along the whole curve (not restarted per segment)."""
    period, phase = dash + gap, 0.0
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        seg = math.hypot(x1 - x0, y1 - y0)
        s = 0.0
        while s < seg:
            on = phase < dash
            step = min(seg - s, (dash - phase) if on else (period - phase))
            if on and step > 0:
                a, b = s / seg, (s + step) / seg
                dr.line([x0 + (x1 - x0) * a, y0 + (y1 - y0) * a, x0 + (x1 - x0) * b, y0 + (y1 - y0) * b], fill=fill,
                        width=width)
            s += step
            phase = (phase + step) % period


def coverage_curve(img, x, y, w, h, series, lo, hi, xlabel, marks=(), ylabel="fraction of the full oracle") -> None:
    """Cumulative counts / denominator against log10 threshold.  series: (values, denominator, colour, width, dashed)."""
    dr = ImageDraw.Draw(img)
    dr.rectangle([x, y, x + w, y + h], fill=S.WHITE)
    pad_l, pad_b = 58, 46
    px0, py0, pw, ph = x + pad_l, y + 30, w - pad_l - 16, h - pad_b - 30

    def X(v):
        return px0 + pw * (v - lo) / (hi - lo)
    for k in range(5):
        yy = py0 + ph - ph * k / 4
        dr.line([px0, yy, px0 + pw, yy], fill=S.GRID, width=1)
        caption(dr, px0 - 6, yy, f"{k / 4:.2f}", size=12, fill=S.INK2, anchor="rm")
    for k, (mv, lab) in enumerate(marks):
        S.dashed_line(dr, [(X(mv), py0), (X(mv), py0 + ph)], S.MUTED, width=1, dash=4, gap=3)
        caption(dr, X(mv) + 3, py0 + 2 + 15 * (k % 2), lab, size=12, fill=S.INK2)
    xs = np.linspace(lo, hi, 300)
    for vals, den, col, wd, dashed in series:
        v = np.asarray(vals, np.float64)
        v = np.sort(v[np.isfinite(v)])
        if not den:
            continue
        ys = np.searchsorted(v, 10.0 ** xs, side="right") / den
        pts = [(X(a), py0 + ph - ph * min(b, 1.0)) for a, b in zip(xs, ys)]
        if dashed:
            dashed_poly(dr, pts, col, width=wd)
        else:
            dr.line(pts, fill=col, width=wd)
    for t in range(int(math.ceil(lo)), int(math.floor(hi)) + 1):
        dr.line([X(t), py0 + ph, X(t), py0 + ph + 4], fill=S.INK2)
        caption(dr, X(t), py0 + ph + 6, f"1e{t}", size=12, fill=S.INK2, anchor="ma")
    caption(dr, px0 + pw / 2, y + h - 2, xlabel, size=13, fill=S.INK2, anchor="md")
    caption(dr, x + 6, y + 6, ylabel, size=12, fill=S.INK2)
    dr.rectangle([x, y, x + w, y + h], outline=S.INK2)


def curve_key(img, x, y) -> None:
    dr = ImageDraw.Draw(img)
    dr.line([x, y + 10, x + 34, y + 10], fill=C_SGBM, width=3)
    caption(dr, x + 42, y, "SGBM: count ≤ x / full oracle (effective coverage)", size=14)
    dashed_poly(dr, [(x + 470, y + 10), (x + 504, y + 10)], C_SGBM, width=2)
    caption(dr, x + 512, y, "SGBM: count ≤ x / SGBM evaluable (precision)", size=14)
    dr.line([x + 920, y + 10, x + 954, y + 10], fill=C_PRIM, width=2)
    caption(dr, x + 962, y, "AB1d2 primitive (4096 spp): effective coverage", size=14)
    dashed_poly(dr, [(x + 1390, y + 10), (x + 1424, y + 10)], C_PRIM, width=2)
    caption(dr, x + 1432, y, "AB1d2 primitive: precision", size=14)


# ------------------------------------------------------------------ text blocks
def cmp_lines(d: Data, z: Gaze) -> list[str]:
    c = d.per(z)["comparison_ab1d2"]
    p, s = c["primitive_ab1d2"], c["sgbm"]
    cat = c["categories_on_full_oracle"]
    return [f"                 primitive  →  SGBM",
            f"valid           {p['valid_count']:>8,}  →  {s['valid_count']:,}",
            f"oracle coverage {f3(p['oracle_coverage'])}  →  {f3(s['oracle_coverage'])}",
            f"median |err|    {f3(p['median_px'], '{:.2f}')}  →  {f3(s['median_px'], '{:.2f}')} px",
            f"≤ 1 px (prec.)  {f3(p['within_px_precision']['1'])}  →  {f3(s['within_px_precision']['1'])}",
            f"> 10 px          {f3(p['catastrophic_fraction_of_evaluable']['>10px'])}  →  "
            f"{f3(s['catastrophic_fraction_of_evaluable']['>10px'])}",
            f"both {cat['both_correct']['fraction']:.3f} · SGBM only {cat['sgbm_only']['fraction']:.3f} · "
            f"prim only {cat['primitive_only']['fraction']:.3f} · neither {cat['neither']['fraction']:.3f}"]


def metric_lines(d: Data, z: Gaze) -> list[str]:
    m = d.per(z)["metric"]["vs_perfect"]
    w = m["within_m"]
    out = [f"3-D vs perfect: median {fmt_len(qv(m['error_3d_m'], 'median'))}, p90 {fmt_len(qv(m['error_3d_m'], 'p90'))}"]
    for t in ("0.012", "0.025", "0.05", "0.1"):
        out.append(f"≤ {float(t) * 1e3:g} mm: precision {f3(w[t]['precision'])} · effective {f3(w[t]['effective_oracle_coverage'])}")
    return out


def attr_lines(z: Gaze) -> list[str]:
    a = {x["stage"]: x["remaining"] for x in z.asum["attrition"]}
    r = z.ssum["raster"]
    return [f"rectified raster: SGBM-left valid {r['sgbm_left_valid']:,} / {r['pixels']:,}; full validity {r['valid']:,}",
            f"raw core {a['raw_core']:,} → rectifiable {a['rectifiable']:,} → footprint valid {a['footprint_term_roi']:,}",
            f"→ raw product {a['raw_inside']:,}  ({z.ssum['seconds']:.2f} s SGBM)"]


# ------------------------------------------------------------------ figures
def overview(d: Data) -> Image.Image:
    W, H = 2400, 2780
    img = Image.new("RGB", (W, H), S.SURFACE)
    header(img, "Active Bootstrap-1d3 — one-shot SGBM viability",
           ["On the SAME accepted 4096-spp observations, does the frozen semi-global SGBM resolve enough of the residual "
            "correspondence ambiguity to give coherent, operationally useful local metric geometry?", SAME, NOT_STATEMENT],
           [ORA, DER, REF])
    ax, aw = 40, W - 80
    ay, ah = 162, 420
    region(img, ax, ay, aw, ah, "A", "SAME 4096-SPP OBSERVATIONS (raw 256 × 256 core; linear_to_u8, no stretch)", [ORA])
    s = 300
    for z in d.gz:
        x0 = ax + 20 + z.k * 772
        gaze_tag(img, x0, ay + 58, z, size=16)
        for c2, lab in enumerate(("left eye", "right eye")):
            xx = x0 + c2 * (s + 16)
            img.paste(core_view(z.rgb[c2], s), (xx, ay + 88))
            frame(ImageDraw.Draw(img), xx, ay + 88, s, s)
            caption(ImageDraw.Draw(img), xx, ay + 88 + s + 4, f"{lab} · raw core", size=14, fill=S.INK2)
    by, bh = ay + ah + 20, 560
    region(img, ax, by, aw, bh, "B", "SGBM SPATIAL MATCHING — PLANAR INTERNALLY (full 640 × 640 rectified raster)", [DER])
    s = 236
    for z in d.gz:
        x0 = ax + 20 + z.k * 772
        gaze_tag(img, x0, by + 58, z, size=16)
        ol = z.outline()
        rect = np.asarray(Image.fromarray(u8(z.sg["rgb_left"])))
        paste_raster(img, rect, x0, by + 90, s, None, ol)
        arr, m = disp_layer(z.sg, s)
        paste_raster(img, arr, x0 + s + 10, by + 90, s, m, ol)
        arr, m = first_fail_layer(z.sg)
        paste_raster(img, arr, x0 + 2 * (s + 10), by + 90, s, None, ol)
        dr = ImageDraw.Draw(img)
        for k2, lab in enumerate(("rectified left", "refined disparity (valid)", "validity: first failing term")):
            caption(dr, x0 + k2 * (s + 10), by + 90 + s + 4, lab, size=13, fill=S.INK2)
        stat_lines(img, x0, by + 90 + s + 30, attr_lines(z), size=14, step=22)
    dr = ImageDraw.Draw(img)
    caption(dr, ax + 20, by + bh - 62, "Dashed outline: the raw 256 × 256 left core mapped into the rectified raster.  The "
            "disparity is bilinearly sampled there and converted back to RAW right coordinates (section 8).", size=14,
            fill=S.INK2)
    colorbar(img, ax + 20, by + bh - 26, 260, 12, 0, SP.NUM_DISPARITIES, ends=DISP_RAMP, label="", fmt="{:g} px")
    legend(img, ax + 330, by + bh - 34, [(n, c) for n, c in LOSS_LEGEND[:5]] + [("VALID", VALID_TONE)], step=280, size=14)
    cy, ch = by + bh + 20, 640
    region(img, ax, cy, aw, ch, "C", "RAW-CORE CORRESPONDENCE QUALITY (post-freeze; the SAME AB1c oracle; same log scale)",
           [DER, REF])
    legend(img, ax + 20, cy + 54, [(CAT_NAMES[k], CAT_COLORS[k]) for k in SP.CATEGORIES], step=330)
    hatch_legend(img, ax + 20 + 4 * 330, cy + 54, "no oracle / not evaluable")
    s = 236
    for z in d.gz:
        x0 = ax + 20 + z.k * 772
        gaze_tag(img, x0, cy + 88, z, size=16)
        for k2, (arr_m, lab) in enumerate(((err_layer(z.ev["primitive_e_px_core"]), "|err| primitive (AB1d2, 4096)"),
                                           (err_layer(z.ev["sgbm_e_px_core"]), "|err| SGBM"),
                                           (cat_layer(z.ev["category_map"]), "≤ 1 px category"))):
            paste(img, arr_m[0], x0 + k2 * (s + 10), cy + 120, s, arr_m[1])
            caption(ImageDraw.Draw(img), x0 + k2 * (s + 10), cy + 120 + s + 4, lab, size=13, fill=S.INK2)
        stat_lines(img, x0, cy + 120 + s + 30, cmp_lines(d, z), size=14, step=22)
    colorbar(img, ax + aw - 340, cy + ch - 34, 300, 14, 0.01, 300, ends=ERR_RAMP, label="|err| px (log ramp)", fmt="{:g}")
    dy0 = cy + ch + 20
    dh = H - dy0 - 30
    region(img, ax, dy0, aw, dh, "D", "METRIC CONSEQUENCE (accepted spherical geometry on the SGBM raw correspondence)",
           [DER, REF])
    curve_key(img, ax + 20, dy0 + 54)
    s = 236
    for z in d.gz:
        x0 = ax + 20 + z.k * 772
        gaze_tag(img, x0, dy0 + 88, z, size=16)
        arr, m = e3_layer(z.ev["sgbm_e3_core"])
        paste(img, arr, x0, dy0 + 120, s, m)
        caption(ImageDraw.Draw(img), x0, dy0 + 120 + s + 4, "SGBM ‖P − P_perfect‖", size=13, fill=S.INK2)
        stat_lines(img, x0 + s + 14, dy0 + 124, metric_lines(d, z), size=14, step=24)
        n_o = d.per(z)["counts"]["full_oracle"]
        ne = d.per(z)["counts"]["sgbm_valid_and_oracle"]
        pe = d.per(z)["comparison_ab1d2"]["primitive_ab1d2"]["evaluable"]
        pv = z.ev["primitive_e3_core"]
        coverage_curve(img, x0, dy0 + 120 + s + 30, 740, dh - s - 250,
                       [(z.ev["error_3d_vs_perfect_m"], n_o, C_SGBM, 3, False), (z.ev["error_3d_vs_perfect_m"], ne, C_SGBM, 2, True),
                        (pv, n_o, C_PRIM, 2, False), (pv, pe, C_PRIM, 2, True)],
                       -4.0, 1.0, "3-D error threshold x [m] (vs AB1c perfect)",
                       marks=[(math.log10(0.012), "12 mm"), (math.log10(0.025), "25 mm"), (math.log10(0.05), "50 mm"),
                              (math.log10(0.1), "100 mm")])
    colorbar(img, ax + aw - 340, H - 74, 300, 14, 0.1, 316, ends=ERR_RAMP, label="3-D error mm (log ramp)", fmt="{:g}")
    caption(ImageDraw.Draw(img), ax + 20, H - 62, "12 / 25 / 50 / 100 mm marks are descriptive (12 mm = the existing "
            "persistent-map support radius); no acceptance threshold.", size=14, fill=S.INK2)
    return img


def sgbm_vs_primitive(d: Data) -> Image.Image:
    W, H = 2400, 1000
    img = Image.new("RGB", (W, H), S.SURFACE)
    header(img, "Where semi-global aggregation helps and hurts — SGBM vs the accepted AB1d2 primitive matcher",
           ["Same raw-core oracle pixels, same 4096-spp photons.  'Correct' = evaluable and |pixel-equivalent error| ≤ 1 "
            "px; no output counts as not correct.", "Right map: log10(|err SGBM| / |err primitive|) where BOTH are "
            "evaluable (blue: SGBM better, vermilion: primitive better)."], [DER, REF])
    legend(img, 40, 142, [(CAT_NAMES[k], CAT_COLORS[k]) for k in SP.CATEGORIES], step=330)
    hatch_legend(img, 40 + 4 * 330, 142, "no oracle / not evaluable by both")
    s = 360
    for z in d.gz:
        x0 = 40 + z.k * 790
        gaze_tag(img, x0, 180, z)
        arr, m = cat_layer(z.ev["category_map"])
        paste(img, arr, x0, 216, s, m)
        a, b = z.ev["sgbm_e_px_core"], z.ev["primitive_e_px_core"]
        with np.errstate(invalid="ignore", divide="ignore"):
            r = np.log10(np.maximum(np.abs(a), 1e-3) / np.maximum(np.abs(b), 1e-3))
        both = np.isfinite(a) & np.isfinite(b)
        out = np.zeros((N * N, 3), np.uint8)
        out[:] = NOCORR
        out[both] = diverging(np.clip(r[both], -2, 2) / 2)
        paste(img, out.reshape(N, N, 3), x0 + s + 16, 216, s, ~both.reshape(N, N))
        dr = ImageDraw.Draw(img)
        caption(dr, x0, 216 + s + 4, "≤ 1 px category (full oracle)", size=13, fill=S.INK2)
        caption(dr, x0 + s + 16, 216 + s + 4, "log10 error ratio (common evaluable)", size=13, fill=S.INK2)
        stat_lines(img, x0, 216 + s + 34, cmp_lines(d, z), size=15, step=26)
        c = d.per(z)["comparison_ab1d2"]
        ce = c["common_evaluable"]
        stat_lines(img, x0, 216 + s + 34 + 7 * 26 + 10, [
            f"common evaluable {ce['count']:,}: median |err| {f3(ce['median_px_primitive'], '{:.2f}')} → "
            f"{f3(ce['median_px_sgbm'], '{:.2f}')} px; ≤ 1 px {f3(ce['within_1px_primitive'])} → {f3(ce['within_1px_sgbm'])}",
            f"> 100 px: {f3(c['primitive_ab1d2']['catastrophic_fraction_of_evaluable']['>100px'])} → "
            f"{f3(c['sgbm']['catastrophic_fraction_of_evaluable']['>100px'])} (fraction of each matcher's evaluable)"],
            size=15, step=26)
    colorbar(img, W - 380, H - 60, 300, 14, -2, 2, div=True, label="log10 |err SGBM| / |err primitive|", fmt="{:+g}")
    caption(ImageDraw.Draw(img), W - 400, H - 58, "blue (< 0): SGBM better · vermilion (> 0): primitive better", size=14,
            fill=S.INK2, anchor="ra")
    return img


def disparity_validity(d: Data) -> Image.Image:
    W, H = 2400, 1160
    img = Image.new("RGB", (W, H), S.SURFACE)
    header(img, "SGBM disparity and validity on the full rectified raster (planar, internal to the matcher)",
           ["The accepted FSG / AB1a RGB-only SGBM_3WAY: block 5, P1 200, P2 800, uniqueness 10, preFilterCap 31, no "
            "speckle filter, numDisparities 112, LR ≤ 1 px, texture ≥ 0.5 u8, z_rect 0.75 .. 4.5 m, ROI, support.",
            "Hatched = invalid (never hidden).  Dashed outline: the raw left core in rectified coordinates."], [ORA, DER])
    legend(img, 40, 142, [("SGBM left invalid", S.OI_VERM), ("right valid / raster / LR", S.OI_ORANGE),
                          ("texture", S.OI_YELLOW), ("finite / z_rect", S.OI_SKY), ("support / ROI", S.OI_PURPLE),
                          ("VALID", VALID_TONE)], step=300)
    s = 360
    for z in d.gz:
        x0 = 40 + z.k * 790
        gaze_tag(img, x0, 180, z)
        ol = z.outline()
        paste_raster(img, np.asarray(Image.fromarray(u8(z.sg["rgb_left"]))), x0, 216, s, None, ol)
        arr, m = disp_layer(z.sg, s)
        paste_raster(img, arr, x0 + s + 16, 216, s, m, ol)
        arr, _ = first_fail_layer(z.sg)
        paste_raster(img, arr, x0, 216 + s + 40, s, None, ol)
        dr = ImageDraw.Draw(img)
        caption(dr, x0, 216 + s + 4, "rectified left (linear_to_u8)", size=13, fill=S.INK2)
        caption(dr, x0 + s + 16, 216 + s + 4, "refined disparity, 0 .. 112 px", size=13, fill=S.INK2)
        caption(dr, x0, 216 + 2 * s + 44, "first failing validity term", size=13, fill=S.INK2)
        dd = z.ssum["distributions_full_raster_valid"]
        pa = z.asum["passes_alone_at_footprint"]
        lines = ["full raster (640 × 640):", f"  SGBM-left valid {z.ssum['raster']['sgbm_left_valid']:,}",
                 f"  full validity {z.ssum['raster']['valid']:,}",
                 f"  refined d median {f3(qv(dd['refined_disparity_px'], 'median'), '{:.2f}')} px",
                 f"  refinement |Δ| p95 {f3(qv(dd['refinement_delta_px'], 'p95'), '{:+.3f}')} px",
                 f"  LR residual p95 {f3(qv(dd['lr_residual_px'], 'p95'), '{:.3f}')} px",
                 "raw-core footprints passing alone:"] + [f"  {t[5:]} {pa[t]:,}" for t in SP.TERMS]
        stat_lines(img, x0 + s + 16, 216 + s + 40, lines, size=14, step=21)
    colorbar(img, W - 380, H - 50, 300, 14, 0, SP.NUM_DISPARITIES, ends=DISP_RAMP, label="refined disparity px", fmt="{:g}")
    return img


def metric_error(d: Data) -> Image.Image:
    W, H = 2400, 1240
    img = Image.new("RGB", (W, H), S.SURFACE)
    header(img, "Metric consequence — the accepted spherical geometry on the SGBM and primitive correspondences",
           ["‖P − P_perfect‖ against the accepted AB1c perfect spherical reconstruction (REFERENCE, post-freeze).  "
            "Effective coverage counts against the FULL oracle; precision against the matcher's own evaluable output.",
            "12 / 25 / 50 / 100 mm marks are descriptive (12 mm = persistent-map support radius)."], [DER, REF])
    curve_key(img, 40, 142)
    s = 340
    for z in d.gz:
        x0 = 40 + z.k * 790
        gaze_tag(img, x0, 180, z)
        for k2, (vals, lab) in enumerate(((z.ev["primitive_e3_core"], "primitive (AB1d2)"), (z.ev["sgbm_e3_core"], "SGBM"))):
            arr, m = e3_layer(vals)
            paste(img, arr, x0 + k2 * (s + 16), 216, s, m)
            caption(ImageDraw.Draw(img), x0 + k2 * (s + 16), 216 + s + 4, f"3-D error, {lab}", size=13, fill=S.INK2)
        n_o = d.per(z)["counts"]["full_oracle"]
        ne = d.per(z)["counts"]["sgbm_valid_and_oracle"]
        pe = d.per(z)["comparison_ab1d2"]["primitive_ab1d2"]["evaluable"]
        coverage_curve(img, x0, 216 + s + 34, 740, 340,
                       [(z.ev["error_3d_vs_perfect_m"], n_o, C_SGBM, 3, False), (z.ev["error_3d_vs_perfect_m"], ne, C_SGBM, 2, True),
                        (z.ev["primitive_e3_core"], n_o, C_PRIM, 2, False), (z.ev["primitive_e3_core"], pe, C_PRIM, 2, True)],
                       -4.0, 1.0, "3-D error threshold x [m]",
                       marks=[(math.log10(0.012), "12 mm"), (math.log10(0.025), "25 mm"), (math.log10(0.05), "50 mm"),
                              (math.log10(0.1), "100 mm")])
        mp = d.per(z)["metric"]
        lines = metric_lines(d, z) + [
            f"vs Position: median {fmt_len(qv(mp['vs_position']['error_3d_m'], 'median'))}, ≤ 12 mm precision "
            f"{f3(mp['vs_position']['within_m']['0.012']['precision'])}",
            f"secondary (planar Q vs spherical, truth-free): max "
            f"{fmt_len(qv(d.per(z)['secondary']['planar_q_vs_spherical_m'], 'max'))}"]
        stat_lines(img, x0, 216 + s + 390, lines, size=14, step=22)
    colorbar(img, W - 380, H - 50, 300, 14, 0.1, 316, ends=ERR_RAMP, label="3-D error mm (log ramp; saturates)",
             fmt="{:g}")
    return img


def attrition(d: Data) -> Image.Image:
    W, H = 2400, 1100
    img = Image.new("RGB", (W, H), S.SURFACE)
    header(img, "Attrition — SGBM's built-in rejection is part of the result (no post-hoc filter)",
           ["Per gaze, the 65,536 raw left-core pixels through rectification, every SGBM validity term at the 2 × 2 "
            "bilinear footprint (implementation order), and the raw adapter.", "Reference sets (post-freeze): full "
            "oracle, SGBM-serviceable oracle (inside the frozen operating domain), SGBM valid ∩ oracle."], [DER, REF])
    legend(img, 40, 142, LOSS_LEGEND, step=280, size=14)
    s = 300
    for z in d.gz:
        x0 = 40 + z.k * 790
        gaze_tag(img, x0, 180, z)
        arr, _ = loss_layer(z.ad)
        paste(img, arr, x0, 216, s)
        caption(ImageDraw.Draw(img), x0, 216 + s + 4, "where each raw-core pixel is lost", size=13, fill=S.INK2)
        att = z.asum["attrition"]
        k = d.per(z)["counts"]
        rows = [(a["stage"].replace("footprint_term_", "footprint: "), a["remaining"], S.INK2) for a in att]
        rows += [("full oracle", k["full_oracle"], S.REF_BROWN), ("SGBM-serviceable oracle", k["serviceable_oracle"],
                                                                 S.REF_BROWN),
                 ("SGBM valid ∩ oracle", k["sgbm_valid_and_oracle"], C_SGBM),
                 ("SGBM valid ∩ serviceable", k["sgbm_valid_and_serviceable"], C_SGBM)]
        dr = ImageDraw.Draw(img)
        bx, bw, step = x0, 740, 30
        y0 = 216 + s + 34
        for i, (name, val, col) in enumerate(rows):
            yy = y0 + i * step
            frac = val / (N * N)
            dr.rectangle([bx + 300, yy + 4, bx + 300 + (bw - 420) * frac, yy + step - 6], fill=col)
            caption(dr, bx, yy + 4, name, size=13)
            caption(dr, bx + bw, yy + 4, f"{val:,}", size=13, anchor="ra")
    return img


FIGURE_FUNCS = {"overview.png": overview, "sgbm-vs-primitive.png": sgbm_vs_primitive,
                "disparity-validity.png": disparity_validity, "metric-error.png": metric_error, "attrition.png": attrition}


def displays() -> dict:
    return {"images": "fsg_stereo.linear_to_u8 RGB (raw core and the rectified left), no stretch",
            "error_maps": "log10 |px err| ramp 0.01 .. 316 px, identical for SGBM and the primitive matcher",
            "metric_maps": "log10 3-D error ramp 0.1 mm .. 316 mm (saturates above), identical for both",
            "disparity": "refined disparity 0 .. 112 px linear ramp on SGBM-valid pixels; invalid hatched",
            "invalid": "no-correspondence tone WITH a diagonal hatch; never hidden"}


def render_all(run: Path, rgb_paths: dict | None = None) -> tuple[dict, Data]:
    d = Data(run, rgb_paths)
    return {name: fn(d) for name, fn in FIGURE_FUNCS.items()}, d


def visualize(run: Path, vis: Path, rgb_paths: dict | None = None) -> dict:
    vis.mkdir(parents=True, exist_ok=True)
    figs, d = render_all(run, rgb_paths)
    out = {}
    for name in SP.FIGURES:
        (vis / name).write_bytes(png_bytes(figs[name]))
        out[name] = {"sha256": sha256(vis / name), "badges": BADGES[name], "size": list(figs[name].size)}
    man = {"schema": "AB1d3-visuals-manifest-v1", "figures": out, "sources": d.sources, "displays": displays(),
           "regenerate": ".venv/bin/python tools/active_bootstrap/ab1d3_run.py visualize --run RUN --visuals VIS",
           "style": "Visual Language 1 (tools/visual_language/style.py)", "fonts": S.font_hashes(), "statement": SAME}
    (vis / "visuals-manifest.json").write_text(json.dumps(man, indent=1, sort_keys=True) + "\n")
    print(f"[ab1d3] visualize: {len(out)} figures -> {vis}")
    return man
