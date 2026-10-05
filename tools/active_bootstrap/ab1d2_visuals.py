"""Active Bootstrap-1d2: the persistent human-facing figures of the 4096-spp observation-quality control.

Contract: docs/active-bootstrap/ab1d2-4096spp-observation-quality-contract.md, section 20.  Reads the AB1d2 run, the
accepted AB1d run (the paired 256-spp records and evaluation), the accepted AB1c 256-spp observations and the pinned
AB1d visuals manifest (the twelve accepted example pixels, reused in order; nothing is chosen after seeing 4096
results).  Draws with Visual Language 1 (``style.py``) and the accepted AB1b / AB1c / AB1d figure helpers (read-only).

Display transforms: every image panel shows ``fsg_stereo.linear_to_u8`` RGB (the matcher's own photometric transfer),
identical for 256 and 4096.  The zoomed crops additionally carry ONE contrast stretch per gaze, computed from the
256-spp crop and applied unchanged to the 4096-spp crop; those panels are labelled "CONTRAST-STRETCHED" on the figure,
and their limits are recorded in the manifest.  Truth classes are text badges.  Deterministic: the checker regenerates
every PNG byte-identically.
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
import ab1d_match as M  # noqa: E402  (accepted matcher; landscapes only)
import ab1d2_spec as SP  # noqa: E402
import fsg_stereo as FS  # noqa: E402  (accepted photometric transfer, read-only)
import style as S  # noqa: E402  (Visual Language 1, read-only)

ORA, DER, REF = SP.TRUTH_ORACLE, SP.TRUTH_DERIVED, SP.TRUTH_REFERENCE
BADGES = {"overview.png": [ORA, DER, REF], "paired-cost-landscapes.png": [ORA, DER, REF],
          "correspondence-improvement.png": [DER, REF], "observation-comparison.png": [ORA, DER, REF],
          "metric-comparison.png": [DER, REF], "confidence-change.png": [DER, REF]}
SAME = "SAME scene · SAME gaze · SAME calibration · SAME seeds (L 2111, R 2112) · SAME matcher · 256 → 4096 spp ONLY"
NOT_STATEMENT = ("No matcher change (5×5 ZNCC, texture 0.5 u8, full interval), no denoising, no new gaze, no head motion, "
                 "no controller.  Benchmark: the accepted AB1c perfect correspondence, post-freeze, for BOTH conditions.")
GAZE_COLORS = [S.OI_BLUE, S.OI_VERM, S.OI_GREEN]
C256, C4096, ORC_C = S.INK2, S.OI_BLUE, S.OI_VERM
TRANS_COLORS = {"bad_to_good": S.OI_GREEN, "good_to_good": S.OI_SKY, "good_to_bad": S.OI_VERM, "bad_to_bad": (214, 211, 204)}
TRANS_NAMES = {"bad_to_good": ">1 px → ≤1 px", "good_to_good": "≤1 px → ≤1 px", "good_to_bad": "≤1 px → >1 px",
               "bad_to_bad": ">1 px → >1 px"}
ZOOM_HALF = 24                                   # zoom crop: raw rows / cols 296..343 (the core centre), fixed
STRETCH_Q = (0.02, 0.98)
caption, stat_lines, region, header, frame, histogram = (BV.caption, BV.stat_lines, BV.region, BV.header, BV.frame,
                                                         BV.histogram)
png_bytes, diverging, colorbar = BV.png_bytes, BV.diverging, BV.colorbar
fmt_len, qv = CV.fmt_len, CV.qv
ERR_RAMP = BV.ERR_RAMP


def sha256(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def npz(path: Path) -> dict:
    with np.load(path, allow_pickle=False) as z:
        return {k: np.asarray(z[k]) for k in z.files}


def j(path: Path):
    return json.loads(Path(path).read_text())


class Gaze:
    def __init__(self, run: Path, g: str, k: int, examples: list[tuple[str, int]]):
        self.g, self.k, self.tab = g, k, SP.GAZE_TABLE[g]
        self.c = j(run / SP.obs_rel(g, "calibration.json"))
        o4, o2 = npz(run / SP.obs_rel(g, "rgb-observation.npz")), npz(SP.a1c_acq(g, "rgb-observation.npz"))
        self.rgb = {"256": (o2["rgb_L"], o2["rgb_R"]), "4096": (o4["rgb_L"], o4["rgb_R"])}
        self.rec = {"256": npz(SP.a1d(f"match/{g}/matcher-record.npz")), "4096": npz(run / f"match/{g}/matcher-record.npz")}
        self.evr = {"256": npz(SP.a1d(f"evaluation/{g}/evaluation-result.npz")),
                    "4096": npz(run / f"evaluation/{g}/evaluation-result.npz")}
        self.par = npz(run / f"evaluation/{g}/paired-result.npz")
        self.examples = examples
        self.files = ([run / SP.obs_rel(g, n) for n in ("calibration.json", "rgb-observation.npz")]
                      + [run / f"match/{g}/matcher-record.npz", run / f"evaluation/{g}/evaluation-result.npz",
                         run / f"evaluation/{g}/paired-result.npz", SP.a1c_acq(g, "rgb-observation.npz"),
                         SP.a1d(f"match/{g}/matcher-record.npz"), SP.a1d(f"evaluation/{g}/evaluation-result.npz")])
        self._ctx = {}
        self.stretch = stretch_limits(self.rgb["256"][0])

    def ctx(self, cond: str):
        if cond not in self._ctx:
            self._ctx[cond] = M.Context(self.c, M.gray(self.rgb[cond][0]), M.gray(self.rgb[cond][1]))
        return self._ctx[cond]

    def grid(self, idx, values) -> np.ndarray:
        n = SP.CORE_SIZE
        out = np.full(n * n, np.nan)
        out[np.asarray(idx, np.int64)] = values
        return out.reshape(n, n)

    def label(self) -> str:
        return f"gaze {self.k + 1}: ({self.tab['yaw_deg']:+.2f}°, {self.tab['pitch_deg']:+.2f}°)"


class Data:
    def __init__(self, run: Path):
        self.run = run
        self.ev = j(run / "evaluation/evaluation-summary.json")
        man = j(SP.A1D_VIS_MANIFEST[0])
        self.examples = {g: [(e["rule"], int(e["core_index"])) for e in man["examples"][g]] for g in SP.GAZES}
        self.gz = [Gaze(run, g, k, self.examples[g]) for k, g in enumerate(SP.GAZES)]
        self.sources = {"evaluation/evaluation-summary.json": sha256(run / "evaluation/evaluation-summary.json"),
                        str(SP.A1D_VIS_MANIFEST[0]): sha256(SP.A1D_VIS_MANIFEST[0])}
        for z in self.gz:
            for p in z.files:
                p = Path(p)
                self.sources[str(p.relative_to(run)) if p.is_relative_to(run) else str(p)] = sha256(p)


# ------------------------------------------------------------------ display transforms (recorded in the manifest)
def u8(rgb) -> np.ndarray:
    return FS.linear_to_u8(rgb).astype(np.uint8)


def zoom_box() -> tuple[int, int, int, int]:
    c = SP.CORE_ORIGIN + SP.CORE_SIZE // 2
    return c - ZOOM_HALF, c + ZOOM_HALF, c - ZOOM_HALF, c + ZOOM_HALF


def stretch_limits(rgb256_l) -> tuple[float, float]:
    """One stretch per gaze, from the 256-spp left zoom crop (u8 gray percentiles); applied unchanged to 4096."""
    r0, r1, c0, c1 = zoom_box()
    g = M.gray(rgb256_l)[r0:r1, c0:c1]
    lo, hi = (float(np.quantile(g, q)) for q in STRETCH_Q)
    return lo, max(hi, lo + 1.0)


def core_view(rgb, size) -> Image.Image:
    o, n = SP.CORE_ORIGIN, SP.CORE_SIZE
    return Image.fromarray(u8(rgb[o:o + n, o:o + n])).resize((size, size), Image.NEAREST)


def zoom_view(rgb, size, lim=None) -> Image.Image:
    r0, r1, c0, c1 = zoom_box()
    a = u8(rgb[r0:r1, c0:c1]).astype(np.float64)
    if lim is not None:
        a = np.clip((a - lim[0]) / (lim[1] - lim[0]), 0, 1) * 255
    return Image.fromarray(np.rint(a).astype(np.uint8)).resize((size, size), Image.NEAREST)


def stretched_label(img, x, y, w, lim) -> None:
    dr = ImageDraw.Draw(img)
    txt = f"CONTRAST-STRETCHED u8 {lim[0]:.0f}..{lim[1]:.0f} → 0..255 (same limits for 256 and 4096)"
    w = max(w, S.font(14, True).getlength(txt) + 14)
    dr.rectangle([x, y, x + w, y + 24], fill=S.OI_YELLOW)
    caption(dr, x + 6, y + 3, txt, size=14, bold=True)


def gaze_tag(img, x, y, z: Gaze, size=18) -> None:
    dr = ImageDraw.Draw(img)
    S.crosshair(dr, x + 12, y + 13, r=10, solid=True, color=GAZE_COLORS[z.k])
    S.text(dr, (x + 30, y), z.label(), size=size, bold=True, outline=None)


def paste(img, arr, x, y, size, hatch_mask=None) -> None:
    CV.paste_core(img, arr, x, y, size, hatch_mask)


def log_err_map(z: Gaze, cond: str) -> tuple[np.ndarray, np.ndarray]:
    e = z.evr[cond]
    g = z.grid(e["core_index"], np.abs(e["e_px"]))
    m = np.isfinite(g)
    out = np.zeros(g.shape + (3,), np.uint8)
    out[:] = BV.NOCORR
    out[m] = BV.ramp((np.log10(np.maximum(g[m], 1e-3)) + 2.0) / 4.5, ERR_RAMP)     # 0.01 .. ~300 px
    return out, ~m


def delta_map(z: Gaze) -> tuple[np.ndarray, np.ndarray]:
    g = z.grid(z.par["core_index"], z.par["delta_E"])
    m = np.isfinite(g)
    t = np.sign(g[m]) * np.minimum(1.0, np.log10(1 + np.abs(g[m])) / math.log10(101))
    out = np.zeros(g.shape + (3,), np.uint8)
    out[:] = BV.NOCORR
    out[m] = diverging(t)
    return out, ~m


def transition_map(z: Gaze) -> tuple[np.ndarray, np.ndarray]:
    n = SP.CORE_SIZE
    idx = z.par["core_index"].astype(np.int64)
    g0, g1 = z.par["E256"] <= SP.GOOD_PX, z.par["E4096"] <= SP.GOOD_PX
    out = np.zeros((n * n, 3), np.uint8)
    out[:] = BV.NOCORR
    for key, m in (("bad_to_good", ~g0 & g1), ("good_to_good", g0 & g1), ("good_to_bad", g0 & ~g1), ("bad_to_bad", ~g0 & ~g1)):
        out[idx[m]] = TRANS_COLORS[key]
    have = np.zeros(n * n, bool)
    have[idx] = True
    return out.reshape(n, n, 3), ~have.reshape(n, n)


def e3_map(z: Gaze, cond: str) -> tuple[np.ndarray, np.ndarray]:
    e = z.evr[cond]
    g = z.grid(e["core_index"], e["error_3d_vs_perfect_m"])
    m = np.isfinite(g)
    out = np.zeros(g.shape + (3,), np.uint8)
    out[:] = BV.NOCORR
    out[m] = BV.ramp((np.log10(np.maximum(g[m], 1e-4)) + 4.0) / 3.5, ERR_RAMP)      # 0.1 mm .. ~3 m
    return out, ~m


def fq(d, key, fmt="{:.3f}") -> str:
    v = None if not d else d.get(key)
    return "—" if v is None else fmt.format(v)


def cnt(t: dict, key: str) -> str:
    return f"{t[key]['count']:,} ({t[key]['fraction']:.3f})"


def trans_legend(img, x, y) -> None:
    dr = ImageDraw.Draw(img)
    for k, key in enumerate(TRANS_COLORS):
        xx = x + 300 * k
        dr.rectangle([xx, y + 3, xx + 18, y + 19], fill=TRANS_COLORS[key], outline=S.INK2)
        caption(dr, xx + 26, y, f"{TRANS_NAMES[key]}  (256 → 4096)", size=15)


def curve_legend(img, x, y) -> None:
    dr = ImageDraw.Draw(img)
    dr.line([x, y + 10, x + 34, y + 10], fill=C256, width=2)
    dr.rectangle([x + 12, y + 5, x + 22, y + 15], outline=C256, width=2)
    caption(dr, x + 42, y, "256 spp (accepted AB1d) ZNCC + its natural best (open square)", size=15)
    dr.line([x + 560, y + 10, x + 594, y + 10], fill=C4096, width=3)
    dr.ellipse([x + 571, y + 4, x + 583, y + 16], fill=C4096)
    caption(dr, x + 602, y, "4096 spp ZNCC + its natural best (filled dot)", size=15)
    S.dashed_line(dr, [(x + 1040, y), (x + 1040, y + 20)], ORC_C, width=2, dash=5, gap=3)
    caption(dr, x + 1050, y, "ORACLE-ON-CURVE (REFERENCE, post-freeze; same for both)", size=15)


def landscape_pair(img, x, y, w, h, z: Gaze, i: int, title: str) -> dict:
    """The full frozen ZNCC curve of one left pixel at 256 and at 4096 spp, with ORACLE-ON-CURVE and both picks."""
    dr = ImageDraw.Draw(img)
    dr.rectangle([x, y, x + w, y + h], fill=S.WHITE)
    lc = {c: M.landscape(z.ctx(c), i) for c in ("256", "4096")}
    s_all = np.concatenate([lc[c]["s"] for c in lc])
    lo_s, hi_s = float(s_all.min()), float(s_all.max())
    pad_l, pad_b, pad_t = 52, 30, 56
    px0, py0, pw, ph = x + pad_l, y + pad_t, w - pad_l - 12, h - pad_b - pad_t
    caption(dr, x + 8, y + 6, title, size=15, bold=True)

    def X(s):
        return px0 + pw * (s - lo_s) / max(hi_s - lo_s, 1e-9)

    def Y(v):
        return py0 + ph * (1 - (v + 1) / 2)
    for v in (-1, -0.5, 0, 0.5, 1):
        dr.line([px0, Y(v), px0 + pw, Y(v)], fill=S.GRID, width=1)
        caption(dr, px0 - 6, Y(v), f"{v:+.1f}", size=12, fill=S.INK2, anchor="rm")
    for c, col, wd in (("256", C256, 1), ("4096", C4096, 2)):
        sc, ss = lc[c]["score"], lc[c]["s"]
        ok = np.isfinite(sc)
        pts = [(X(s), Y(v)) for s, v in zip(ss[ok], sc[ok])]
        for a, b in zip(pts[:-1], pts[1:]):
            if abs(a[0] - b[0]) < pw * 3 / max(len(pts), 1) + 2:
                dr.line([a, b], fill=col, width=wd)
    info = {}
    for c in ("256", "4096"):
        r = z.rec[c]
        if r["valid_match"][i]:
            sb, zb = float(r["k_best"][i]) * 1.0, float(r["best_zncc"][i])
            if c == "256":
                dr.rectangle([X(sb) - 6, Y(zb) - 6, X(sb) + 6, Y(zb) + 6], outline=C256, width=2)
            else:
                dr.ellipse([X(sb) - 5, Y(zb) - 5, X(sb) + 5, Y(zb) + 5], fill=C4096)
        e = z.evr[c]
        pos = np.nonzero(e["core_index"] == i)[0]
        if pos.size:
            info[c] = {"e": float(e["e_px"][pos[0]]), "rank": int(e["oracle_rank"][pos[0]]),
                       "zo": float(e["zncc_oracle"][pos[0]]), "s_oc": float(e["s_oracle_on_curve"][pos[0]])}
    if "4096" in info or "256" in info:
        s_oc = info.get("4096", info.get("256"))["s_oc"]
        S.dashed_line(dr, [(X(s_oc), py0), (X(s_oc), py0 + ph)], ORC_C, width=2, dash=6, gap=4)
    caption(dr, px0, y + h - 4, f"line s {lo_s:.0f}", size=12, fill=S.INK2, anchor="ld")
    caption(dr, px0 + pw, y + h - 4, f"{hi_s:.0f} px (nearer →)", size=12, fill=S.INK2, anchor="rd")

    def rk(v):
        return ">8" if v > 8 else str(v)
    if "256" in info and "4096" in info:
        a, b = info["256"], info["4096"]
        caption(dr, x + 8, y + 28, f"|err| {abs(a['e']):.2f} → {abs(b['e']):.2f} px;  oracle rank {rk(a['rank'])} → "
                f"{rk(b['rank'])};  oracle ZNCC {a['zo']:.3f} → {b['zo']:.3f}", size=14, fill=S.INK)
    dr.rectangle([x, y, x + w, y + h], outline=S.INK2)
    return info


def histogram2(img, x, y, w, h, a, b, edges, xlabel, ticks=None, legend="(grey 256, blue 4096)") -> None:
    """Two overlaid step histograms (grey first series, blue second); values outside the edges fall in the end bins."""
    dr = ImageDraw.Draw(img)
    dr.rectangle([x, y, x + w, y + h], fill=S.WHITE)
    cn = []
    for v in (a, b):
        v = np.asarray(v, np.float64)
        v = v[np.isfinite(v)]
        cn.append(np.histogram(np.clip(v, edges[0], edges[-1]), bins=edges)[0] if v.size else np.zeros(len(edges) - 1))
    top = max(1, int(max(c.max() for c in cn)))
    pad_l, pad_b = 64, 42
    px0, py0, pw, ph = x + pad_l, y + 10, w - pad_l - 14, h - pad_b - 10
    for k in range(5):
        yy = py0 + ph - ph * k / 4
        dr.line([px0, yy, px0 + pw, yy], fill=S.GRID, width=1)
        caption(dr, px0 - 6, yy, f"{int(round(top * k / 4)):,}", size=12, fill=S.INK2, anchor="rm")
    nb = len(edges) - 1
    bw = pw / nb
    for c, col, wd in ((cn[0], C256, 2), (cn[1], C4096, 3)):
        pts = []
        for k in range(nb):
            yy = py0 + ph - ph * c[k] / top
            pts += [(px0 + k * bw, yy), (px0 + (k + 1) * bw, yy)]
        dr.line(pts, fill=col, width=wd)
    dr.line([px0, py0 + ph, px0 + pw, py0 + ph], fill=S.INK2, width=1)
    for t in (ticks if ticks is not None else np.linspace(edges[0], edges[-1], 5)):
        tv, lab = (t if isinstance(t, tuple) else (t, f"{t:.3g}"))
        xx = px0 + pw * (tv - edges[0]) / (edges[-1] - edges[0])
        dr.line([xx, py0 + ph, xx, py0 + ph + 4], fill=S.INK2)
        caption(dr, xx, py0 + ph + 6, lab, size=12, fill=S.INK2, anchor="ma")
    caption(dr, px0 + pw / 2, y + h - 2, f"{xlabel}   {legend}", size=13, fill=S.INK2, anchor="md")
    dr.rectangle([x, y, x + w, y + h], outline=S.INK2)


def cdf2(img, x, y, w, h, a, b, lo, hi, xlabel, marks=()) -> None:
    """Empirical CDFs of log10 values at 256 (grey) and 4096 (blue)."""
    dr = ImageDraw.Draw(img)
    dr.rectangle([x, y, x + w, y + h], fill=S.WHITE)
    pad_l, pad_b = 54, 42
    px0, py0, pw, ph = x + pad_l, y + 12, w - pad_l - 16, h - pad_b - 12

    def X(v):
        return px0 + pw * (v - lo) / (hi - lo)
    for k in range(5):
        yy = py0 + ph - ph * k / 4
        dr.line([px0, yy, px0 + pw, yy], fill=S.GRID, width=1)
        caption(dr, px0 - 6, yy, f"{k / 4:.2f}", size=12, fill=S.INK2, anchor="rm")
    for k, (mv, lab) in enumerate(marks):
        S.dashed_line(dr, [(X(mv), py0), (X(mv), py0 + ph)], S.MUTED, width=1, dash=4, gap=3)
        caption(dr, X(mv) + 3, py0 + 2 + 15 * k, lab, size=12, fill=S.INK2)
    for v, col, wd in ((a, C256, 2), (b, C4096, 3)):
        v = np.sort(np.log10(np.maximum(np.asarray(v, np.float64)[np.isfinite(v)], 10.0 ** lo)))
        if v.size == 0:
            continue
        qs = np.linspace(0, 1, 400)
        xs = np.clip(np.quantile(v, qs), lo, hi)
        dr.line([(X(xv), py0 + ph - ph * q) for xv, q in zip(xs, qs)], fill=col, width=wd)
    for t in range(int(math.ceil(lo)), int(math.floor(hi)) + 1):
        dr.line([X(t), py0 + ph, X(t), py0 + ph + 4], fill=S.INK2)
        caption(dr, X(t), py0 + ph + 6, f"1e{t}", size=12, fill=S.INK2, anchor="ma")
    caption(dr, px0 + pw / 2, y + h - 2, xlabel + "   (grey 256, blue 4096)", size=13, fill=S.INK2, anchor="md")
    dr.rectangle([x, y, x + w, y + h], outline=S.INK2)


def paired_lines(d: Data, z: Gaze) -> list[str]:
    p = d.ev["per_gaze"][z.g]["paired"]
    e, t, zn, rk = p["error"], p["transitions_1px"], p["zncc"], p["ranks"]
    return [f"common evaluable {p['counts']['common']:,}",
            f"median |err| {e['median_E256']:.2f} → {e['median_E4096']:.2f} px (ΔE median {e['median_delta_E']:+.3f})",
            f"improved {e['fraction_improved']:.3f} · equal {e['fraction_equal']:.3f} · worsened {e['fraction_worsened']:.3f}",
            f"≤1 px {e['within_1px_256']:.3f} → {e['within_1px_4096']:.3f};  >1→≤1 {cnt(t, 'bad_to_good')}",
            f"≤1→>1 {cnt(t, 'good_to_bad')}",
            f"oracle top-1 {rk['top_fractions_256']['top1']:.3f} → {rk['top_fractions_4096']['top1']:.3f};  oracle ZNCC "
            f"median {fq(zn['Z256'], 'median')} → {fq(zn['Z4096'], 'median')}"]


# ------------------------------------------------------------------ figures
def overview(d: Data) -> Image.Image:
    W, H = 2400, 2560
    img = Image.new("RGB", (W, H), S.SURFACE)
    header(img, "Active Bootstrap-1d2 — 4096-spp observation-quality control",
           ["Does substantially reducing Monte Carlo rendering noise materially improve the SAME frozen primitive "
            "natural correspondence matcher?", SAME, NOT_STATEMENT], [ORA, DER, REF])
    ax, aw = 40, W - 80
    # A
    ay, ah = 162, 700
    region(img, ax, ay, aw, ah, "A", "SAME VIEW, ONE CHANGED VARIABLE (left eye; linear_to_u8, identical for both)", [ORA])
    s = 330
    for z in d.gz:
        x0 = ax + 20 + z.k * 772
        gaze_tag(img, x0, ay + 60, z, size=16)
        for c2, cond in enumerate(("256", "4096")):
            xx = x0 + c2 * (s + 16)
            img.paste(core_view(z.rgb[cond][0], s), (xx, ay + 92))
            frame(ImageDraw.Draw(img), xx, ay + 92, s, s)
            caption(ImageDraw.Draw(img), xx, ay + 92 + s + 4, f"{cond} spp · nominal core 256×256", size=14, fill=S.INK2)
            img.paste(zoom_view(z.rgb[cond][0], 200, z.stretch), (xx, ay + 92 + s + 58))
            frame(ImageDraw.Draw(img), xx, ay + 92 + s + 58, 200, 200)
            caption(ImageDraw.Draw(img), xx + 206, ay + 92 + s + 60, f"{cond} spp", size=14, bold=True)
            caption(ImageDraw.Draw(img), xx + 206, ay + 92 + s + 82, f"zoom {2 * ZOOM_HALF}×{2 * ZOOM_HALF}", size=13,
                    fill=S.INK2)
            caption(ImageDraw.Draw(img), xx + 206, ay + 92 + s + 102, "core centre", size=13, fill=S.INK2)
        stretched_label(img, x0, ay + 92 + s + 28, 2 * s + 16, z.stretch)
    # B
    by, bh = ay + ah + 20, 380
    region(img, ax, by, aw, bh, "B", "SAME PIXELS, PAIRED COST LANDSCAPES (accepted AB1d 'median-error' example per gaze)",
           [ORA, DER, REF])
    curve_legend(img, ax + 20, by + 56)
    for z in d.gz:
        x0 = ax + 20 + z.k * 772
        ex = dict(z.examples)
        i = ex["median-error"]
        gaze_tag(img, x0, by + 90, z, size=16)
        landscape_pair(img, x0, by + 120, 740, 240, z, i, f"median-error example (core {i // SP.CORE_SIZE}, "
                                                         f"{i % SP.CORE_SIZE})")
    # C
    cy, ch = by + bh + 20, 560
    region(img, ax, cy, aw, ch, "C", "CORRESPONDENCE CHANGE (post-freeze; the SAME AB1c oracle for both)", [DER, REF])
    trans_legend(img, ax + 20, cy + 56)
    s = 228
    for z in d.gz:
        x0 = ax + 20 + z.k * 772
        gaze_tag(img, x0, cy + 92, z, size=16)
        for k2, (arr, mask, lab) in enumerate((log_err_map(z, "256") + ("|err| 256",), log_err_map(z, "4096") + ("|err| 4096",),
                                               transition_map(z) + ("1-px transition",))):
            paste(img, arr, x0 + k2 * (s + 12), cy + 124, s, mask)
            caption(ImageDraw.Draw(img), x0 + k2 * (s + 12), cy + 124 + s + 4, lab, size=13, fill=S.INK2)
        stat_lines(img, x0, cy + 124 + s + 30, paired_lines(d, z), size=14, step=22)
    caption(ImageDraw.Draw(img), ax + 20, cy + ch - 26, "|err| maps: log ramp 0.01 .. 300 px (same scale for 256 and 4096); "
            "grey hatch: not evaluable", size=14, fill=S.INK2)
    colorbar(img, ax + aw - 340, cy + ch - 34, 300, 14, 0.01, 300, ends=ERR_RAMP, label="|err| px (log ramp)", fmt="{:g}")
    # D
    dy0 = cy + ch + 20
    dh = H - dy0 - 30
    region(img, ax, dy0, aw, dh, "D", "METRIC CONSEQUENCE (natural spherical reconstruction vs AB1c perfect)", [DER, REF])
    s = 240
    for z in d.gz:
        x0 = ax + 20 + z.k * 772
        gaze_tag(img, x0, dy0 + 56, z, size=16)
        for k2, cond in enumerate(("256", "4096")):
            arr, mask = e3_map(z, cond)
            paste(img, arr, x0 + k2 * (s + 12), dy0 + 88, s, mask)
            caption(ImageDraw.Draw(img), x0 + k2 * (s + 12), dy0 + 88 + s + 4, f"3-D error {cond}", size=13, fill=S.INK2)
        a = d.ev["per_gaze"][z.g]["accepted_256"]["metric"]["vs_perfect"]
        b = d.ev["per_gaze"][z.g]["absolute_4096"]["metric"]["vs_perfect"]
        pm = d.ev["per_gaze"][z.g]["paired"]["metric"]
        stat_lines(img, x0 + 2 * (s + 12), dy0 + 92, [
            "vs AB1c perfect (3-D)", f"median {fmt_len(qv(a['error_3d_m'], 'median'))}",
            f"  → {fmt_len(qv(b['error_3d_m'], 'median'))}", f"p95 {fmt_len(qv(a['error_3d_m'], 'p95'))}",
            f"  → {fmt_len(qv(b['error_3d_m'], 'p95'))}",
            f"≤12 mm {fq(a['fraction_3d_within_m'], '0.012')} → {fq(b['fraction_3d_within_m'], '0.012')}",
            f"improved {fq(pm, 'fraction_improved')}"], size=14, step=24, bold_first=True)
        cdf2(img, x0, dy0 + 88 + s + 30, 740, 230, z.evr["256"]["error_3d_vs_perfect_m"],
             z.evr["4096"]["error_3d_vs_perfect_m"], -4.5, 1.0, "‖P_nat − P_perfect‖ [m], CDF",
             marks=[(math.log10(0.012), "12 mm"), (math.log10(0.05), "50 mm")])
    colorbar(img, ax + aw - 340, H - 74, 300, 14, 0.1, 3000, ends=ERR_RAMP, label="3-D error mm (log ramp)", fmt="{:g}")
    caption(ImageDraw.Draw(img), ax + 20, H - 62, "3-D maps: log ramp 0.1 mm .. 3 m.  12 mm = persistent-map support radius "
            "(descriptive; not a threshold).", size=14, fill=S.INK2)
    return img


def paired_cost_landscapes(d: Data) -> Image.Image:
    rows = max(len(z.examples) for z in d.gz)
    W, H = 2400, 236 + rows * 300 + 30
    img = Image.new("RGB", (W, H), S.SURFACE)
    header(img, "Paired cost landscapes — the frozen ZNCC at 256 and 4096 spp, same pixels",
           ["All twelve examples are the ACCEPTED AB1d figure pixels (pinned AB1d visuals manifest, same order); none is "
            "chosen after seeing 4096 results.", SAME], [ORA, DER, REF])
    curve_legend(img, 40, 156)
    for z in d.gz:
        x0 = 40 + z.k * 790
        gaze_tag(img, x0, 192, z, size=16)
        for r, (name, i) in enumerate(z.examples):
            landscape_pair(img, x0, 226 + r * 300, 760, 280, z, i, f"{name}  (core {i // SP.CORE_SIZE}, {i % SP.CORE_SIZE})")
    return img


def correspondence_improvement(d: Data) -> Image.Image:
    W, H = 2400, 1300
    img = Image.new("RGB", (W, H), S.SURFACE)
    header(img, "Correspondence change — paired |pixel-equivalent error| at 256 and 4096 spp (same oracle)",
           ["ΔE = E4096 − E256 on the common evaluable set: blue = improved (4096 smaller), vermilion = worsened, light = "
            f"unchanged (|ΔE| ≤ {SP.EQUAL_TOL_PX:g} px).", "1 px is a descriptive bin, not an acceptance threshold."],
           [DER, REF])
    trans_legend(img, 40, 140)
    s = 232
    for z in d.gz:
        x0 = 40 + z.k * 790
        gaze_tag(img, x0, 176, z)
        for k2, (arr, mask, lab) in enumerate((log_err_map(z, "256") + ("|err| 256 (log 0.01..300)",),
                                               log_err_map(z, "4096") + ("|err| 4096 (same scale)",),
                                               delta_map(z) + ("ΔE (sign · log, ±100 px)",))):
            paste(img, arr, x0 + k2 * (s + 14), 212, s, mask)
            caption(ImageDraw.Draw(img), x0 + k2 * (s + 14), 212 + s + 4, lab, size=13, fill=S.INK2)
        arr, mask = transition_map(z)
        paste(img, arr, x0, 212 + s + 34, s, mask)
        caption(ImageDraw.Draw(img), x0, 212 + 2 * s + 38, "1-px transition class", size=13, fill=S.INK2)
        dE = z.par["delta_E"]
        sl = np.sign(dE) * np.log10(1 + np.abs(dE))
        histogram(img, x0 + s + 14, 212 + s + 34, 2 * s + 14, s, sl, np.linspace(-2.6, 2.6, 53), S.OI_BLUE,
                  "ΔE (sign · log10(1+|ΔE|))", ticks=[(-2, "−99"), (-1, "−9"), (0, "0"), (1, "+9"), (2, "+99")])
        e0, e1 = np.abs(z.par["E256"]), np.abs(z.par["E4096"])
        histogram2(img, x0, 212 + 2 * s + 70, 760, 260, np.log10(np.maximum(e0, 1e-3)), np.log10(np.maximum(e1, 1e-3)),
                   np.linspace(-3, 2.7, 58), "log10 |pixel-equivalent error|",
                   ticks=[(-3, "0.001"), (-2, "0.01"), (-1, "0.1"), (0, "1"), (1, "10"), (2, "100")])
        p = d.ev["per_gaze"][z.g]["paired"]
        e = p["error"]
        stat_lines(img, x0, 212 + 2 * s + 350, paired_lines(d, z) + [
            f"ΔE p10 / p50 / p90: {fq(e['delta_E'], 'p10', '{:+.2f}')} / {fq(e['delta_E'], 'median', '{:+.2f}')} / "
            f"{fq(e['delta_E'], 'p90', '{:+.2f}')} px",
            f"improved by >1 px {e['improved_by_more_than_1px']:.3f};  worsened by >1 px {e['worsened_by_more_than_1px']:.3f}"],
            size=14, step=23)
    colorbar(img, W - 380, 104, 300, 16, -100, 100, div=True, label="ΔE [px]: blue improved · vermilion worsened",
             fmt="{:+.0f}")
    colorbar(img, W - 760, 104, 300, 16, 0.01, 300, ends=ERR_RAMP, label="|err| px (log ramp)", fmt="{:g}")
    return img


def observation_comparison(d: Data) -> Image.Image:
    W, H = 2400, 1640
    img = Image.new("RGB", (W, H), S.SURFACE)
    header(img, "Observation comparison — the same view rendered at 256 and 4096 spp",
           ["Images: linear_to_u8, identical for both conditions (zoom crops additionally CONTRAST-STRETCHED, labelled).  "
            "|ΔG| is the change between two renders, not a noise estimate.", "PROXY values are labelled PROXY and are "
            "never converted into a sensor-noise variance."], [ORA, DER, REF])
    s = 236
    for z in d.gz:
        x0 = 40 + z.k * 790
        gaze_tag(img, x0, 140, z)
        for r2, eye in enumerate(("L", "R")):
            e_i = 0 if eye == "L" else 1
            yy = 176 + r2 * (s + 40)
            for c2, cond in enumerate(("256", "4096")):
                xx = x0 + c2 * (s + 10)
                img.paste(core_view(z.rgb[cond][e_i], s), (xx, yy))
                frame(ImageDraw.Draw(img), xx, yy, s, s)
                caption(ImageDraw.Draw(img), xx, yy + s + 2, f"{eye} core · {cond} spp", size=13, fill=S.INK2)
            gd = M.gray(z.rgb["4096"][e_i]) - M.gray(z.rgb["256"][e_i])
            o, n = SP.CORE_ORIGIN, SP.CORE_SIZE
            arr = BV.ramp(np.abs(gd[o:o + n, o:o + n]) / 10.0, ERR_RAMP)
            paste(img, arr, x0 + 2 * (s + 10), yy, s)
            caption(ImageDraw.Draw(img), x0 + 2 * (s + 10), yy + s + 2, f"{eye} |G4096 − G256| 0..10 u8", size=13, fill=S.INK2)
        yy = 176 + 2 * (s + 40)
        for c2, cond in enumerate(("256", "4096")):
            xx = x0 + c2 * (s + 10)
            img.paste(zoom_view(z.rgb[cond][0], s, z.stretch), (xx, yy + 28))
            frame(ImageDraw.Draw(img), xx, yy + 28, s, s)
            caption(ImageDraw.Draw(img), xx, yy + s + 30, f"L zoom · {cond} spp", size=13, fill=S.INK2)
        stretched_label(img, x0, yy, 2 * s + 10, z.stretch)
        img.paste(zoom_view(z.rgb["256"][0], s), (x0 + 2 * (s + 10), yy + 28))
        frame(ImageDraw.Draw(img), x0 + 2 * (s + 10), yy + 28, s, s)
        caption(ImageDraw.Draw(img), x0 + 2 * (s + 10), yy + s + 30, "L zoom · 256 · NOT stretched", size=13, fill=S.INK2)
        yh = yy + s + 60
        gl = M.gray(z.rgb["4096"][0]) - M.gray(z.rgb["256"][0])
        gr = M.gray(z.rgb["4096"][1]) - M.gray(z.rgb["256"][1])
        histogram2(img, x0, yh, 760, 200, gl.ravel(), gr.ravel(), np.linspace(-15, 15, 61),
                   "G4096 − G256 [u8], full raster", legend="(grey L eye, blue R eye; ends clipped)")
        dg = d.ev["per_gaze"][z.g]["paired"]
        histogram2(img, x0, yh + 214, 370, 200, z.rec["256"]["left_patch_std_u8"], z.rec["4096"]["left_patch_std_u8"],
                   np.linspace(0, 20, 41), "left patch std u8 (≥20 last bin)")
        histogram2(img, x0 + 390, yh + 214, 370, 200, z.par["Z256"], z.par["Z4096"], np.linspace(-1, 1, 41),
                   "oracle ZNCC")
        dd = dg["diagnostics"]
        gcl, gcr = dd["gray_change"]["L"], dd["gray_change"]["R"]
        stat_lines(img, x0, yh + 432, [
            f"|ΔG| L core median / p90 / p95: {fq(gcl['core']['abs'], 'median', '{:.2f}')} / "
            f"{fq(gcl['core']['abs'], 'p90', '{:.2f}')} / {fq(gcl['core']['abs'], 'p95', '{:.2f}')} u8; mean ΔG "
            f"{gcl['core']['signed_mean']:+.3f}",
            f"|ΔG| R core median / p90 / p95: {fq(gcr['core']['abs'], 'median', '{:.2f}')} / "
            f"{fq(gcr['core']['abs'], 'p90', '{:.2f}')} / {fq(gcr['core']['abs'], 'p95', '{:.2f}')} u8; mean ΔG "
            f"{gcr['core']['signed_mean']:+.3f}",
            f"left patch std median {fq(dd['left_patch_std_all']['256'], 'median', '{:.2f}')} → "
            f"{fq(dd['left_patch_std_all']['4096'], 'median', '{:.2f}')} u8",
            f"PROXY-LR (oracle L−R robust std) {dd['PROXY_LR']['256']:.2f} → {dd['PROXY_LR']['4096']:.2f} u8",
            f"PROXY-HP (left high-pass robust std) {dd['PROXY_HP']['256']:.2f} → {dd['PROXY_HP']['4096']:.2f} u8"],
            size=14, step=23)
    return img


def metric_comparison(d: Data) -> Image.Image:
    W, H = 2400, 1060
    img = Image.new("RGB", (W, H), S.SURFACE)
    header(img, "Metric consequence — accepted AB1b spherical geometry on the 256 and 4096 natural correspondences",
           ["‖P_natural − P_perfect‖ against the SAME accepted AB1c perfect spherical reconstruction (REFERENCE, "
            "post-freeze).", "12 / 25 / 50 mm marks are descriptive (12 mm = persistent-map support radius)."], [DER, REF])
    s = 360
    for z in d.gz:
        x0 = 40 + z.k * 790
        gaze_tag(img, x0, 140, z)
        for k2, cond in enumerate(("256", "4096")):
            arr, mask = e3_map(z, cond)
            paste(img, arr, x0 + k2 * (s + 20), 176, s, mask)
            caption(ImageDraw.Draw(img), x0 + k2 * (s + 20), 176 + s + 4, f"log10 3-D error, {cond} spp (0.1 mm .. 3 m)",
                    size=13, fill=S.INK2)
        cdf2(img, x0, 176 + s + 34, 740, 300, z.evr["256"]["error_3d_vs_perfect_m"], z.evr["4096"]["error_3d_vs_perfect_m"],
             -4.5, 1.0, "‖P_nat − P_perfect‖ [m], CDF",
             marks=[(math.log10(0.012), "12 mm"), (math.log10(0.025), "25 mm"), (math.log10(0.05), "50 mm")])
        a = d.ev["per_gaze"][z.g]["accepted_256"]["metric"]
        b = d.ev["per_gaze"][z.g]["absolute_4096"]["metric"]
        pm = d.ev["per_gaze"][z.g]["paired"]["metric"]
        lines = []
        for name, lab in (("vs_perfect", "vs perfect"), ("vs_position", "vs Position")):
            qa, qb = a[name]["error_3d_m"], b[name]["error_3d_m"]
            fa, fb = a[name]["fraction_3d_within_m"], b[name]["fraction_3d_within_m"]
            lines += [f"{lab}: median {fmt_len(qv(qa, 'median'))} → {fmt_len(qv(qb, 'median'))}; p95 "
                      f"{fmt_len(qv(qa, 'p95'))} → {fmt_len(qv(qb, 'p95'))}",
                      f"   ≤12 mm {fq(fa, '0.012')} → {fq(fb, '0.012')};  ≤25 mm {fq(fa, '0.025')} → {fq(fb, '0.025')};  "
                      f"≤50 mm {fq(fa, '0.05')} → {fq(fb, '0.05')}"]
        lines += [f"paired: Δ median {fmt_len(qv(pm['delta_m'], 'median'))}; improved {fq(pm, 'fraction_improved')}; "
                  f"worsened {fq(pm, 'fraction_worsened')}"]
        stat_lines(img, x0, 176 + s + 350, lines, size=14, step=24)
    return img


def confidence_change(d: Data) -> Image.Image:
    W, H = 2400, 760
    img = Image.new("RGB", (W, H), S.SURFACE)
    header(img, "Texture-stratified change — quartiles of the 256-spp left patch std, applied to both conditions",
           ["Bars: median |pixel-equivalent error| (log axis) at 256 (grey) and 4096 (blue).  Dots: oracle top-1 "
            "fraction (right axis 0..1), 256 open / 4096 filled.", "Descriptive only; the texture threshold stays 0.5 u8."],
           [DER, REF])
    pw, ph = 740, 520
    for z in d.gz:
        x0 = 40 + z.k * 790
        gaze_tag(img, x0, 140, z)
        st = d.ev["per_gaze"][z.g]["paired"]["strata_256_texture"]
        dr = ImageDraw.Draw(img)
        y0 = 180
        dr.rectangle([x0, y0, x0 + pw, y0 + ph], fill=S.WHITE)
        bins = [b for b in st["bins"] if b["count"]]
        px0, py0, pww, phh = x0 + 56, y0 + 20, pw - 110, ph - 104
        lo, hi = -2.0, 3.0

        def Y(v):
            return py0 + phh * (1 - (math.log10(max(v, 1e-2)) - lo) / (hi - lo))
        for t in range(-2, 4):
            yy = py0 + phh * (1 - (t - lo) / (hi - lo))
            dr.line([px0, yy, px0 + pww, yy], fill=S.GRID, width=1)
            caption(dr, px0 - 6, yy, f"{10.0 ** t:g}", size=12, fill=S.INK2, anchor="rm")
        bw = pww / max(len(bins), 1)
        for k, b in enumerate(bins):
            xx = px0 + k * bw
            for c2, (key, col) in enumerate((("median_E256", C256), ("median_E4096", C4096))):
                if b[key] is not None:
                    dr.rectangle([xx + 10 + c2 * (bw / 2 - 10), Y(b[key]), xx + (c2 + 1) * (bw / 2 - 10) + 10 - 4, py0 + phh],
                                 fill=(190, 188, 182) if c2 == 0 else col)
            for c2, key in enumerate(("top1_256", "top1_4096")):
                if b[key] is not None:
                    yy = py0 + phh * (1 - b[key])
                    cx = xx + bw / 2 + (c2 * 2 - 1) * 14
                    if c2 == 0:
                        dr.ellipse([cx - 6, yy - 6, cx + 6, yy + 6], outline=S.OI_VERM, width=2)
                    else:
                        dr.ellipse([cx - 6, yy - 6, cx + 6, yy + 6], fill=S.OI_VERM)
            caption(dr, xx + bw / 2, py0 + phh + 6, b["stratum"], size=13, fill=S.INK2, anchor="ma")
            caption(dr, xx + bw / 2, py0 + phh + 24, f"n={b['count']:,}", size=12, fill=S.INK2, anchor="ma")
            caption(dr, xx + bw / 2, py0 + phh + 42, f"{b['median_E256']:.1f}→{b['median_E4096']:.1f} px", size=12,
                    fill=S.INK, anchor="ma")
            caption(dr, xx + bw / 2, py0 + phh + 58, f"top1 {b['top1_256']:.2f}→{b['top1_4096']:.2f}", size=12,
                    fill=S.INK, anchor="ma")
        caption(dr, px0 + pww + 8, py0, "1", size=12, fill=S.INK2)
        caption(dr, px0 + pww + 8, py0 + phh - 12, "0", size=12, fill=S.INK2)
        if st.get("edges"):
            caption(dr, x0 + pw - 8, y0 + 4, "256 texture edges " + ", ".join(f"{e:.2f}" for e in st["edges"]) + " u8",
                    size=12, fill=S.INK2, anchor="ra")
        dr.rectangle([x0, y0, x0 + pw, y0 + ph], outline=S.INK2)
    return img


FIGURE_FUNCS = {"overview.png": overview, "paired-cost-landscapes.png": paired_cost_landscapes,
                "correspondence-improvement.png": correspondence_improvement,
                "observation-comparison.png": observation_comparison, "metric-comparison.png": metric_comparison,
                "confidence-change.png": confidence_change}


def displays(d: Data) -> dict:
    r0, r1, c0, c1 = zoom_box()
    return {"images": "fsg_stereo.linear_to_u8 RGB, identical for 256 and 4096; no stretch",
            "zoom_box_raw_rows_cols": [r0, r1, c0, c1],
            "stretch": {z.g: {"lo_u8": z.stretch[0], "hi_u8": z.stretch[1], "from": "256-spp left zoom crop gray, "
                              f"quantiles {list(STRETCH_Q)}", "applied_to": ["256", "4096"], "label_drawn": True,
                              "label": "CONTRAST-STRETCHED"} for z in d.gz},
            "error_maps": "log10 |px err| ramp 0.01 .. 300 px, identical for 256 and 4096",
            "metric_maps": "log10 3-D error ramp 0.1 mm .. 3 m, identical for 256 and 4096"}


def render_all(run: Path) -> tuple[dict, Data]:
    d = Data(run)
    return {name: fn(d) for name, fn in FIGURE_FUNCS.items()}, d


def visualize(run: Path, vis: Path) -> dict:
    vis.mkdir(parents=True, exist_ok=True)
    figs, d = render_all(run)
    out = {}
    for name in SP.FIGURES:
        (vis / name).write_bytes(png_bytes(figs[name]))
        out[name] = {"sha256": sha256(vis / name), "badges": BADGES[name], "size": list(figs[name].size)}
    man = {"schema": "AB1d2-visuals-manifest-v1", "figures": out, "sources": d.sources,
           "examples": {g: [{"rule": n, "core_index": i} for n, i in d.examples[g]] for g in SP.GAZES},
           "examples_source": {"path": str(SP.A1D_VIS_MANIFEST[0]), "sha256": SP.A1D_VIS_MANIFEST[1]},
           "displays": displays(d),
           "regenerate": ".venv/bin/python tools/active_bootstrap/ab1d2_run.py visualize --run RUN --visuals VIS",
           "style": "Visual Language 1 (tools/visual_language/style.py)", "fonts": S.font_hashes(), "statement": SAME}
    (vis / "visuals-manifest.json").write_text(json.dumps(man, indent=1, sort_keys=True) + "\n")
    print(f"[ab1d2] visualize: {len(out)} figures -> {vis}")
    return man
