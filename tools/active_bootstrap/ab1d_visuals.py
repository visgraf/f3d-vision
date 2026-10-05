"""Active Bootstrap-1d: the persistent human-facing figures of safe-forward natural RGB correspondence.

Contract: docs/active-bootstrap/ab1d-safe-forward-natural-correspondence-contract.md, section 25.  Reads the AB1d run
(matcher records, natural geometry, evaluation) and the reused AB1c observations; draws with Visual Language 1
(``style.py``) and the accepted AB1b / AB1c figure helpers (read-only).

Truth classes (text badges, never colour alone): ORACLE INPUT (the rendered RGB), DERIVED (natural matches, score
landscapes, natural geometry), REFERENCE / EVALUATION (the AB1c perfect correspondence used as a post-freeze benchmark,
ORACLE-ON-CURVE, Position).  Nothing is CONTROLLER-TIME.  Example pixels of the landscapes are chosen by the
deterministic post-freeze rules of contract section 25 (REFERENCE / EVALUATION selections).  Glyphs: solid line = the
raw right epipolar search locus; filled dot = natural best peak; open ring = other distinct peaks; dashed ring =
ORACLE-ON-CURVE (post-freeze reference); hatch = no natural estimate / no oracle.  Deterministic: the checker
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
import ab1d_match as M  # noqa: E402
import ab1d_spec as SP  # noqa: E402
import style as S  # noqa: E402  (Visual Language 1, read-only)

ORA, DER, REF = SP.TRUTH_ORACLE, SP.TRUTH_DERIVED, SP.TRUTH_REFERENCE
FIGURES = ["overview.png", "correspondence-error.png", "cost-landscapes.png", "natural-reconstruction.png",
           "confidence-diagnostics.png"]
BADGES = {"overview.png": [ORA, DER, REF], "correspondence-error.png": [DER, REF], "cost-landscapes.png": [ORA, DER, REF],
          "natural-reconstruction.png": [DER, REF], "confidence-diagnostics.png": [DER, REF]}
NOT_STATEMENT = ("ONE primitive matcher (direct raw epipolar search, 5×5 angular patch, ZNCC, one parabola) on the SAME "
                 "three AB1c observations; geometry fixed (accepted AB1b).")
NOT_STATEMENT2 = ("Not SGBM, not learned, no head motion, no controller.  The AB1c perfect correspondence is a post-freeze "
                  "benchmark only.")
CLOUD_MAX_M = 0.050
GAZE_COLORS = [S.OI_BLUE, S.OI_VERM, S.OI_GREEN]
NAT_C, ORC_C, PEAK_C = S.OI_BLUE, S.OI_VERM, S.OI_ORANGE
ERR_RAMP, COND_RAMP, MARGIN_RAMP = BV.ERR_RAMP, BV.COND_RAMP, BV.DISP_RAMP
caption, stat_lines, region, header, frame, histogram = (BV.caption, BV.stat_lines, BV.region, BV.header, BV.frame,
                                                         BV.histogram)
png_bytes, gamma, ramp, colorbar, statement = BV.png_bytes, BV.gamma, BV.ramp, BV.colorbar, BV.statement
fmt_len, qv = CV.fmt_len, CV.qv
CLASS_COLORS = {0: (0, 114, 178), 1: (213, 94, 0), 2: (153, 153, 153), 3: (232, 230, 225)}
CLASS_NAMES = {0: "oracle ∧ natural (evaluable)", 1: "oracle, natural invalid (miss)", 2: "natural, no oracle (unscored)",
               3: "neither"}


def sha256(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def npz(path: Path) -> dict:
    with np.load(path, allow_pickle=False) as z:
        return {k: np.asarray(z[k]) for k in z.files}


def j(path: Path):
    return json.loads(Path(path).read_text())


class Gaze:
    def __init__(self, run: Path, g: str, k: int):
        self.g, self.k = g, k
        self.tab = SP.GAZE_TABLE[g]
        self.c = j(SP.calibration_path(g))
        obs = npz(SP.rgb_path(g))
        self.rgb_L, self.rgb_R = obs["rgb_L"], obs["rgb_R"]
        self.rec = npz(run / "match" / g / "matcher-record.npz")
        self.msum = j(run / "match" / g / "match-summary.json")
        self.geo = npz(run / "spherical" / g / "epipolar-result.npz")
        self.gsum = j(run / "spherical" / g / "spherical-summary.json")
        self.evr = npz(run / "evaluation" / g / "evaluation-result.npz")
        self.files = [run / "match" / g / "matcher-record.npz", run / "match" / g / "match-summary.json",
                      run / "spherical" / g / "epipolar-result.npz", run / "spherical" / g / "spherical-summary.json",
                      run / "evaluation" / g / "evaluation-result.npz"]
        self.ext = [SP.calibration_path(g), SP.rgb_path(g)]
        n, o = SP.CORE_SIZE, SP.CORE_ORIGIN
        self.core_rgb = self.rgb_L[o:o + n, o:o + n]
        self.cls = self.evr["class_map"].reshape(n, n)
        self._ctx = None

    @property
    def ctx(self):
        if self._ctx is None:
            self._ctx = M.Context(self.c, M.gray(self.rgb_L), M.gray(self.rgb_R))
        return self._ctx

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
        self.gz = [Gaze(run, g, k) for k, g in enumerate(SP.GAZES)]
        self.sources = {"evaluation/evaluation-summary.json": sha256(run / "evaluation/evaluation-summary.json")}
        for z in self.gz:
            for p in z.files:
                self.sources[str(Path(p).relative_to(run))] = sha256(p)
            for p in z.ext:
                self.sources[str(p)] = sha256(p)
        self.examples = {z.g: examples(z) for z in self.gz}


# ------------------------------------------------------------------ deterministic example selection (section 25)
def examples(z: Gaze) -> list[tuple[str, int]]:
    """REFERENCE / EVALUATION selections on the evaluable set; ties -> smallest core index."""
    idx = z.evr["core_index"].astype(np.int64)
    e = np.abs(z.evr["e_px"])
    margin = z.rec["peak_margin"][idx]
    out = []

    def pick(score, mask):
        m = mask & np.isfinite(score)
        if not m.any():
            return None
        best = score[m].min()
        cand = idx[m][score[m] == best]
        return int(cand.min())
    fin = np.isfinite(e)
    out.append(("median-error", pick(np.abs(e - np.median(e[fin])), fin)))
    out.append(("high-confidence low-error", pick(-margin, fin & (e <= 0.25))))
    out.append(("smallest peak margin", pick(margin, fin)))
    out.append(("large-error percentile", pick(np.abs(e - np.quantile(e[fin], 0.99)), fin)))
    return [(name, i) for name, i in out if i is not None]


# ------------------------------------------------------------------ helpers
def core_map(values2d, ends, lo=None, hi=None, log=False):
    g = np.asarray(values2d, np.float64)
    m = np.isfinite(g)
    out = np.zeros(g.shape + (3,), np.uint8)
    out[:] = BV.NOCORR
    if not m.any():
        return out, 0.0, 0.0
    v = np.log10(np.maximum(g[m], 1e-15)) if log else g[m]
    lo = float(np.quantile(v, 0.01)) if lo is None else lo
    hi = float(np.quantile(v, 0.99)) if hi is None else hi
    hi = hi if hi > lo else lo + 1e-12
    out[m] = ramp((v - lo) / (hi - lo), ends)
    return out, lo, hi


def paste(img, arr, x, y, size, hatch_mask=None) -> None:
    CV.paste_core(img, arr, x, y, size, hatch_mask)


def gaze_tag(img, x, y, z: Gaze, size=18) -> None:
    dr = ImageDraw.Draw(img)
    S.crosshair(dr, x + 12, y + 13, r=10, solid=True, color=GAZE_COLORS[z.k])
    S.text(dr, (x + 30, y), z.label(), size=size, bold=True, outline=None)


def raw_view(rgb, size, box=None) -> Image.Image:
    img = Image.fromarray(gamma(rgb)).resize((size, size), Image.BILINEAR)
    dr = ImageDraw.Draw(img)
    s = size / SP.RAW_SIZE
    o, n = SP.CORE_ORIGIN, SP.CORE_SIZE
    S.dashed_rect(dr, [(o - 0.5) * s, (o - 0.5) * s, (o + n - 0.5) * s, (o + n - 0.5) * s], S.WHITE, width=2, dash=8,
                  gap=5)
    return img


def patch_tile(vals, size) -> Image.Image:
    v = np.asarray(vals, np.float64).reshape(SP.PATCH, SP.PATCH)
    if not np.isfinite(v).all():
        return Image.new("RGB", (size, size), BV.NOCORR)
    lo, hi = float(v.min()), float(v.max())
    a = np.clip(np.rint((v - lo) / max(hi - lo, 1e-9) * 255), 0, 255).astype(np.uint8)
    # contrast-stretched per tile for display; rows = theta offset i (along the line), columns = phi offset j
    return Image.fromarray(np.repeat(a[..., None], 3, -1)).resize((size, size), Image.NEAREST)


def local_crop(z: Gaze, i: int, size: int, half: int = 40):
    """Right raw crop around the natural estimate, with the search locus, peaks and ORACLE-ON-CURVE."""
    rec, evr = z.rec, z.evr
    ev_pos = np.nonzero(evr["core_index"] == i)[0]
    uvn = rec["uv_R_est"][i]
    cx, cy = (float(uvn[0]), float(uvn[1])) if np.isfinite(uvn).all() else tuple(rec["q_inf"][i])
    x0, y0 = int(round(cx)) - half, int(round(cy)) - half
    x0, y0 = min(max(x0, 0), SP.RAW_SIZE - 2 * half), min(max(y0, 0), SP.RAW_SIZE - 2 * half)
    crop = gamma(z.rgb_R[y0:y0 + 2 * half, x0:x0 + 2 * half])
    img = Image.fromarray(crop).resize((size, size), Image.NEAREST)
    dr = ImageDraw.Draw(img)
    s = size / (2 * half)

    def px(u, v):
        return (u - x0 + 0.5) * s, (v - y0 + 0.5) * s
    q, t = rec["q_inf"][i], rec["line_dir"][i]
    a, b = px(*(q + (-2000) * t)), px(*(q + 2000 * t))
    dr.line([a, b], fill=S.WHITE, width=4)
    dr.line([a, b], fill=S.INK, width=2)
    for p in range(1, SP.TOP_K):
        uv = rec["peak_uv_R"][i, p]
        if np.isfinite(uv).all():
            x, y = px(*uv)
            S.ring(dr, x, y, r=7, color=PEAK_C, width=2)
    if np.isfinite(uvn).all():
        x, y = px(*uvn)
        dr.ellipse([x - 6, y - 6, x + 6, y + 6], fill=NAT_C, outline=S.WHITE, width=2)
    if ev_pos.size:
        s_oc = evr["s_oracle_on_curve"][ev_pos[0]]
        uv = q + s_oc * t
        x, y = px(*uv)
        S.ring(dr, x, y, r=11, color=ORC_C, width=3, dashed=True)
    dr.rectangle([0, 0, size - 1, size - 1], outline=S.INK2)
    return img


def landscape_panel(img, x, y, w, h, z: Gaze, i: int, title: str) -> None:
    """The full ZNCC curve over the admissible segment (DERIVED) with the post-freeze oracle (REFERENCE)."""
    dr = ImageDraw.Draw(img)
    dr.rectangle([x, y, x + w, y + h], fill=S.WHITE)
    lc = M.landscape(z.ctx, i)
    rec, evr = z.rec, z.evr
    ev_pos = np.nonzero(evr["core_index"] == i)[0]
    s_oc = float(evr["s_oracle_on_curve"][ev_pos[0]]) if ev_pos.size else None
    s_all = lc["s"]
    sc = lc["score"]
    pad_l, pad_b, pad_t = 52, 36, 34
    px0, py0, pw, ph = x + pad_l, y + pad_t, w - pad_l - 12, h - pad_b - pad_t
    lo_s, hi_s = float(s_all.min()), float(s_all.max())
    caption(dr, x + 8, y + 6, title, size=15, bold=True)

    def X(s):
        return px0 + pw * (s - lo_s) / max(hi_s - lo_s, 1e-9)

    def Y(v):
        return py0 + ph * (1 - (v + 1) / 2)
    for v in (-1, -0.5, 0, 0.5, 1):
        dr.line([px0, Y(v), px0 + pw, Y(v)], fill=S.GRID, width=1)
        caption(dr, px0 - 6, Y(v), f"{v:+.1f}", size=12, fill=S.INK2, anchor="rm")
    ok = np.isfinite(sc)
    pts = [(X(s), Y(v)) for s, v in zip(s_all[ok], sc[ok])]
    for a, b in zip(pts[:-1], pts[1:]):
        if abs(a[0] - b[0]) < pw * 3 / max(len(pts), 1) + 2:
            dr.line([a, b], fill=S.INK2, width=1)
    for p in range(1, SP.TOP_K):
        sp = rec["peak_s"][i, p]
        if np.isfinite(sp):
            S.ring(dr, X(sp), Y(rec["peak_zncc"][i, p]), r=5, color=PEAK_C, width=2)
    if rec["valid_match"][i]:
        sb = float(rec["k_best"][i]) * SP.SPACING_PX
        dr.ellipse([X(sb) - 5, Y(rec["best_zncc"][i]) - 5, X(sb) + 5, Y(rec["best_zncc"][i]) + 5], fill=NAT_C)
        dr.line([X(rec["s_est"][i]), py0, X(rec["s_est"][i]), py0 + ph], fill=NAT_C, width=1)
    if s_oc is not None:
        S.dashed_line(dr, [(X(s_oc), py0), (X(s_oc), py0 + ph)], ORC_C, width=2, dash=6, gap=4)
        zo = float(evr["zncc_oracle"][ev_pos[0]])
        if np.isfinite(zo):
            S.ring(dr, X(s_oc), Y(zo), r=8, color=ORC_C, width=2, dashed=True)
    caption(dr, px0, y + h - 4, f"line s {lo_s:.0f}", size=12, fill=S.INK2, anchor="ld")
    caption(dr, px0 + pw, y + h - 4, f"{hi_s:.0f} px (nearer →)", size=12, fill=S.INK2, anchor="rd")
    if ev_pos.size:
        e = float(evr["e_px"][ev_pos[0]])
        caption(dr, px0 + pw, y + 6, f"err {e:+.2f} px; margin {rec['peak_margin'][i]:.3f}; rank "
                f"{'>8' if evr['oracle_rank'][ev_pos[0]] > SP.TOP_K else int(evr['oracle_rank'][ev_pos[0]])}",
                size=13, fill=S.INK, anchor="ra")
    dr.rectangle([x, y, x + w, y + h], outline=S.INK2)


def legend_line(img, x, y) -> None:
    dr = ImageDraw.Draw(img)
    dr.ellipse([x, y + 4, x + 12, y + 16], fill=NAT_C)
    caption(dr, x + 18, y, "natural best (DERIVED)", size=15)
    S.ring(dr, x + 236, y + 10, r=7, color=PEAK_C, width=2)
    caption(dr, x + 250, y, "other distinct peaks (≤ 8)", size=15)
    S.ring(dr, x + 500, y + 10, r=9, color=ORC_C, width=3, dashed=True)
    caption(dr, x + 516, y, "ORACLE-ON-CURVE (REFERENCE, post-freeze)", size=15)


def error_maps(img, x, y, z: Gaze, s: int) -> None:
    """Validity / oracle classes, |pixel-equivalent error| and peak margin on the 256 x 256 raw core."""
    n = SP.CORE_SIZE
    cls = np.zeros((n, n, 3), np.uint8)
    for k, col in CLASS_COLORS.items():
        cls[z.cls == k] = col
    paste(img, cls, x, y, s)
    idx = z.evr["core_index"]
    err, lo, hi = core_map(z.grid(idx, np.abs(z.evr["e_px"])), ERR_RAMP, lo=-2.0, hi=1.0, log=True)
    paste(img, err, x + s + 14, y, s, ~np.isfinite(z.grid(idx, z.evr["e_px"])))
    mg = np.where(z.rec["valid_match"], z.rec["peak_margin"], np.nan).reshape(n, n)
    mar, mlo, mhi = core_map(mg, MARGIN_RAMP, lo=0.0, hi=float(np.nanquantile(mg, 0.95)) if np.isfinite(mg).any() else 1)
    paste(img, mar, x + 2 * (s + 14), y, s, ~np.isfinite(mg))
    dr = ImageDraw.Draw(img)
    caption(dr, x, y + s + 4, "classes (legend)", size=13, fill=S.INK2)
    caption(dr, x + s + 14, y + s + 4, "|px err| 0.01 .. 10 (log)", size=13, fill=S.INK2)
    caption(dr, x + 2 * (s + 14), y + s + 4, f"margin 0 .. {mhi:.2f}", size=13, fill=S.INK2)


def class_legend(img, x, y, horizontal=False) -> None:
    dr = ImageDraw.Draw(img)
    for k in range(4):
        xx, yy = (x + 400 * k, y) if horizontal else (x, y + 26 * k)
        dr.rectangle([xx, yy + 3, xx + 18, yy + 19], fill=CLASS_COLORS[k], outline=S.INK2)
        caption(dr, xx + 26, yy, CLASS_NAMES[k], size=15)


def cloud_sets(evr) -> tuple[list, int]:
    """Perfect points (grey) and natural points within CLOUD_MAX_M of them (blue <= 12 mm, red 12..50 mm)."""
    e3 = evr["error_3d_vs_perfect_m"]
    good = np.isfinite(e3)
    near = good & (e3 <= SP.METRIC_FRACTIONS_M[0])
    mid = good & (e3 > SP.METRIC_FRACTIONS_M[0]) & (e3 <= CLOUD_MAX_M)
    return ([(evr["P_perfect"][good], (180, 180, 180)), (evr["P_natural"][mid], ORC_C), (evr["P_natural"][near], NAT_C)],
            int((good & (e3 > CLOUD_MAX_M)).sum()))


def fr(d: dict | None, key: str) -> str:
    return "—" if not d or d.get(key) is None else f"{d[key]:.3f}"


# ------------------------------------------------------------------ figures
def overview(d: Data) -> Image.Image:
    W, H = 2400, 2560
    img = Image.new("RGB", (W, H), S.SURFACE)
    header(img, "Active Bootstrap-1d — safe-forward natural RGB correspondence",
           ["In favorable geometry, does raw RGB place the right correspondence at the correct spherical epipolar "
            "location?  Geometry is held fixed; this tests CORRESPONDENCE only.", NOT_STATEMENT, NOT_STATEMENT2],
           [ORA, DER, REF])
    ax, aw = 40, W - 80
    # A
    ay, ah = 162, 470
    region(img, ax, ay, aw, ah, "A", "SAME SAVED AB1c OBSERVATIONS (no new render, no new gaze)", [ORA])
    s = 330
    for z in d.gz:
        x0 = ax + 20 + z.k * (2 * s + 12 + 60)
        for i2, rgb in enumerate((z.rgb_L, z.rgb_R)):
            img.paste(raw_view(rgb, s), (x0 + i2 * (s + 12), ay + 64))
            frame(ImageDraw.Draw(img), x0 + i2 * (s + 12), ay + 64, s, s)
        gaze_tag(img, x0, ay + 64 + s + 8, z, size=16)
    caption(ImageDraw.Draw(img), ax + 20, ay + ah - 30, "raw L | raw R per gaze (dashed: nominal 12° core).  Matcher "
            "time reads ONLY calibration.json + rgb-observation.npz (allowlist guard; Position / oracle reads 0).",
            size=16, fill=S.INK2)
    # B
    by, bh = ay + ah + 20, 600
    region(img, ax, by, aw, bh, "B", "DIRECT EPIPOLAR MATCHING on the ORIGINAL right image (median-error examples)",
           [ORA, DER, REF])
    legend_line(img, ax + 20, by + 56)
    for z in d.gz:
        x0 = ax + 20 + z.k * 760
        ex = dict(d.examples[z.g])
        i = ex.get("median-error")
        if i is None:
            continue
        gaze_tag(img, x0, by + 92, z, size=16)
        lp = patch_tile(z.ctx.lp_vals[i], 120)
        img.paste(lp, (x0, by + 130))
        frame(ImageDraw.Draw(img), x0, by + 130, 120, 120)
        caption(ImageDraw.Draw(img), x0, by + 254, "left 5×5 patch", size=13, fill=S.INK2)
        img.paste(local_crop(z, i, 300), (x0 + 140, by + 130))
        caption(ImageDraw.Draw(img), x0 + 140, by + 434, "right raw crop: search locus (line)", size=13, fill=S.INK2)
        landscape_panel(img, x0, by + 456, 720, 130, z, i, "ZNCC along the whole admissible segment")
        r = z.rec
        stat_lines(img, x0 + 456, by + 140, [
            f"core ({i // SP.CORE_SIZE}, {i % SP.CORE_SIZE})",
            f"candidates {int(r['candidate_count'][i])}",
            f"best ZNCC {r['best_zncc'][i]:.3f}",
            f"margin {r['peak_margin'][i]:.3f}",
            f"refined {bool(r['refined'][i])} ({r['refinement_offset_samples'][i]:+.2f})"], size=15, step=26)
    # C
    cy, ch = by + bh + 20, 620
    region(img, ax, cy, aw, ch, "C", "CORRESPONDENCE ERROR (post-freeze; AB1c perfect correspondence as benchmark)",
           [DER, REF])
    class_legend(img, ax + 20, cy + 56)
    s = 230
    for z in d.gz:
        x0 = ax + 20 + z.k * 760
        gaze_tag(img, x0, cy + 170, z, size=16)
        error_maps(img, x0, cy + 204, z, s)
        e = d.ev["per_gaze"][z.g]
        p, c, ln = e["primary"], e["counts"], e["landscape"]
        pf = p["px_equivalent_fractions"] or {}
        stat_lines(img, x0, cy + 204 + s + 30, [
            f"oracle {c['oracle_correspondences']:,}; natural valid {c['natural_valid']:,}; evaluable {c['evaluable']:,}",
            f"coverage {c['coverage']:.3f}; natural non-oracle {c['natural_valid_non_oracle']:,}",
            f"|e_θ| px-equiv median {fr(p['px_equivalent_abs'], 'median')}; p95 {fr(p['px_equivalent_abs'], 'p95')}",
            f"≤0.10 {pf.get('0.1', 0):.3f}  ≤0.25 {pf.get('0.25', 0):.3f}  ≤0.50 {pf.get('0.5', 0):.3f}  "
            f"≤1.00 {pf.get('1', 0):.3f}",
            f"oracle top1 {ln['top_fractions']['top1']:.3f}  top3 {ln['top_fractions']['top3']:.3f}  "
            f">8 {ln['top_fractions']['worse_than_top8']:.3f}"], size=15, step=25)
    # D
    dy0 = cy + ch + 20
    dh = H - dy0 - 30
    region(img, ax, dy0, aw, dh, "D", "METRIC CONSEQUENCE (natural spherical reconstruction vs perfect / Position)",
           [DER, REF])
    s = 300
    for z in d.gz:
        x0 = ax + 20 + z.k * 760
        gaze_tag(img, x0, dy0 + 56, z, size=16)
        evr = z.evr
        sets, n_out = cloud_sets(evr)
        CV.cloud(img, x0, dy0 + 92, s, s, sets, title="top", origin=False)
        e3 = z.grid(evr["core_index"], evr["error_3d_vs_perfect_m"])
        arr, lo, hi = core_map(e3, ERR_RAMP, lo=-4.0, hi=-0.5, log=True)
        paste(img, arr, x0 + s + 20, dy0 + 92, s, ~np.isfinite(e3))
        caption(ImageDraw.Draw(img), x0 + s + 20, dy0 + 92 + s + 4, "log10 ‖P_nat − P_perfect‖: −4 .. −0.5 m",
                size=13, fill=S.INK2)
        m = d.ev["per_gaze"][z.g]["metric"]
        a, b = m["vs_perfect"], m["vs_position"]
        stat_lines(img, x0, dy0 + 92 + s + 30, [
            f"cloud: blue ≤12 mm, red 12–50 mm, grey perfect; {n_out:,} > 50 mm not drawn",
            "natural vs AB1c perfect spherical (3-D):",
            f"  median {fmt_len(qv(a['error_3d_m'], 'median'))}; p95 {fmt_len(qv(a['error_3d_m'], 'p95'))}",
            f"  ≤12 mm {fr(a['fraction_3d_within_m'], '0.012')}; ≤25 mm {fr(a['fraction_3d_within_m'], '0.025')}; "
            f"≤50 mm {fr(a['fraction_3d_within_m'], '0.05')}",
            "natural vs Position (3-D):",
            f"  median {fmt_len(qv(b['error_3d_m'], 'median'))}; p95 {fmt_len(qv(b['error_3d_m'], 'p95'))}; "
            f"≤12 mm {fr(b['fraction_3d_within_m'], '0.012')}",
            f"natural κ median {qv(m['natural_kappa'], 'median') or 0:.1f} (conditioning retained)",
            "12 mm = persistent-map support radius (descriptive; not a threshold)"], size=15, step=25)
    return img


def correspondence_error(d: Data) -> Image.Image:
    W, H = 2400, 1390
    img = Image.new("RGB", (W, H), S.SURFACE)
    header(img, "Correspondence error — natural θ_R vs the AB1c perfect correspondence (post-freeze)",
           ["e_θ = θ_R(natural) − θ_R(oracle) on ORACLE VISIBLE ∧ NATURAL VALID; pixel-equivalent via the local "
            "dθ/ds along the right epipolar line at ORACLE-ON-CURVE.", "Descriptive bins only; no acceptance threshold."],
           [DER, REF])
    s = 300
    for z in d.gz:
        x0 = 40 + z.k * 790
        gaze_tag(img, x0, 150, z)
        error_maps(img, x0, 186, z, 236)
        e = np.abs(z.evr["e_px"])
        edges = np.linspace(-3, 2, 51)
        histogram(img, x0, 480, 740, 300, np.log10(np.maximum(e, 1e-3)), edges, S.OI_BLUE,
                  "log10 |pixel-equivalent error|", ticks=[(-3, "0.001"), (-2, "0.01"), (-1, "0.1"), (0, "1"),
                                                           (1, "10"), (2, "100")])
        sg = z.evr["e_px"]
        histogram(img, x0, 800, 740, 300, np.clip(sg, -2, 2), np.linspace(-2, 2, 81), S.OI_SKY,
                  "signed pixel-equivalent error (clipped to ±2)")
        p = d.ev["per_gaze"][z.g]["primary"]
        pf = p["px_equivalent_fractions"] or {}
        stat_lines(img, x0, 1130, [
            f"|e_θ| median {qv(p['e_theta_abs_rad'], 'median') * 1e6:.1f} µrad; p95 {qv(p['e_theta_abs_rad'], 'p95') * 1e6:.1f}"
            f" µrad; max {qv(p['e_theta_abs_rad'], 'max') * 1e6:.0f} µrad",
            f"signed e_θ p05 / median / p95: {qv(p['e_theta_signed_rad'], 'p05') * 1e6:+.1f} / "
            f"{qv(p['e_theta_signed_rad'], 'median') * 1e6:+.1f} / {qv(p['e_theta_signed_rad'], 'p95') * 1e6:+.1f} µrad",
            f"|px-equiv| median {fr(p['px_equivalent_abs'], 'median')}; p90 {fr(p['px_equivalent_abs'], 'p90')}; "
            f"p95 {fr(p['px_equivalent_abs'], 'p95')}; p99 {fr(p['px_equivalent_abs'], 'p99')}",
            f"focal approx f·|e_θ| median {fr(p['focal_approximation_abs_px'], 'median')}; line Δs median "
            f"{fr(p['line_coordinate_difference_abs_px'], 'median')}",
            f"fractions ≤0.10 / 0.25 / 0.50 / 1.00 px: {pf.get('0.1', 0):.3f} / {pf.get('0.25', 0):.3f} / "
            f"{pf.get('0.5', 0):.3f} / {pf.get('1', 0):.3f}",
            f"ORACLE-ON-CURVE off-line distance max {qv(p['oracle_on_curve_perpendicular_px'], 'max'):.1e} px"],
            size=15, step=27)
    class_legend(img, 40, H - 60, horizontal=True)
    return img


def cost_landscapes(d: Data) -> Image.Image:
    rows = max(len(d.examples[z.g]) for z in d.gz)
    W, H = 2400, 230 + rows * 330 + 40
    img = Image.new("RGB", (W, H), S.SURFACE)
    header(img, "Cost landscapes — the frozen ZNCC along the whole admissible epipolar segment",
           ["Examples chosen by deterministic post-freeze rules (REFERENCE / EVALUATION selections): median-error; "
            "high-confidence low-error; smallest peak margin; large-error (p99).", "Curve, peaks and estimates are "
            "DERIVED; the dashed ORACLE-ON-CURVE marker is a post-freeze REFERENCE."], [ORA, DER, REF])
    legend_line(img, 40, 150)
    for z in d.gz:
        x0 = 40 + z.k * 790
        gaze_tag(img, x0, 186, z, size=16)
        for r, (name, i) in enumerate(d.examples[z.g]):
            y0 = 222 + r * 330
            landscape_panel(img, x0, y0, 740, 190, z, i, f"{name}  (core {i // SP.CORE_SIZE}, {i % SP.CORE_SIZE})")
            lp = patch_tile(z.ctx.lp_vals[i], 100)
            img.paste(lp, (x0, y0 + 200))
            frame(ImageDraw.Draw(img), x0, y0 + 200, 100, 100)
            caption(ImageDraw.Draw(img), x0 + 2, y0 + 302, "left", size=12, fill=S.INK2)
            r_rec = z.rec
            if r_rec["valid_match"][i]:
                th_b = np.array([r_rec["theta_R_discrete"][i]])
                vals, _ = M.patch(z.ctx.cam_r, z.ctx.g_r, th_b, z.ctx.ph_l[[i]], z.ctx.delta)
                img.paste(patch_tile(vals[0], 100), (x0 + 120, y0 + 200))
                frame(ImageDraw.Draw(img), x0 + 120, y0 + 200, 100, 100)
                caption(ImageDraw.Draw(img), x0 + 122, y0 + 302, "right @ best", size=12, fill=S.INK2)
            ev_pos = np.nonzero(z.evr["core_index"] == i)[0]
            if ev_pos.size:
                th_o = np.array([z.evr["theta_R_oracle"][ev_pos[0]]])
                vals, _ = M.patch(z.ctx.cam_r, z.ctx.g_r, th_o, z.ctx.ph_l[[i]], z.ctx.delta)
                img.paste(patch_tile(vals[0], 100), (x0 + 240, y0 + 200))
                frame(ImageDraw.Draw(img), x0 + 240, y0 + 200, 100, 100)
                caption(ImageDraw.Draw(img), x0 + 242, y0 + 302, "right @ oracle (REF)", size=12, fill=S.INK2)
            img.paste(local_crop(z, i, 120, half=24), (x0 + 380, y0 + 200))
            caption(ImageDraw.Draw(img), x0 + 506, y0 + 200, "right raw crop", size=12, fill=S.INK2)
    return img


def natural_reconstruction(d: Data) -> Image.Image:
    W, H = 2400, 1420
    img = Image.new("RGB", (W, H), S.SURFACE)
    header(img, "Natural reconstruction — accepted AB1b spherical geometry on the frozen natural correspondence",
           ["P_nat from the natural product only (DERIVED); compared after the freezes with the AB1c perfect spherical "
            "reconstruction and Blender Position (REFERENCE / EVALUATION).",
            "12 / 25 / 50 mm fractions are descriptive (12 mm = persistent-map support radius)."], [DER, REF])
    s = 360
    for z in d.gz:
        x0 = 40 + z.k * 790
        gaze_tag(img, x0, 150, z)
        evr = z.evr
        sets, n_out = cloud_sets(evr)
        CV.cloud(img, x0, 186, s, s, sets, title="top view", origin=False)
        CV.cloud(img, x0 + s + 20, 186, s, s, sets, title="side view", view="side", origin=False)
        caption(ImageDraw.Draw(img), x0, 186 + s + 4, f"blue: natural ≤12 mm from perfect; red: 12–50 mm; grey: perfect; "
                f"{n_out:,} natural points > 50 mm not drawn", size=13, fill=S.INK2)
        e3 = evr["error_3d_vs_perfect_m"]
        histogram(img, x0, 586, 740, 274, np.log10(np.maximum(e3, 1e-6)), np.linspace(-5, 0.5, 56), S.OI_BLUE,
                  "log10 ‖P_nat − P_perfect‖ [m]", ticks=[(-5, "10 µm"), (-4, "0.1 mm"), (-3, "1 mm"),
                                                         (math.log10(0.012), "12 mm"), (-1, "0.1 m"), (0, "1 m")])
        rad = evr["radial_signed_vs_position_m"]
        histogram(img, x0, 880, 740, 260, np.clip(rad, -0.1, 0.1), np.linspace(-0.1, 0.1, 81), S.OI_SKY,
                  "signed radial error vs Position [m] (clipped to ±0.1 m)")
        m = d.ev["per_gaze"][z.g]["metric"]
        a, b = m["vs_perfect"], m["vs_position"]
        stat_lines(img, x0, 1160, [
            f"vs perfect: 3-D median {fmt_len(qv(a['error_3d_m'], 'median'))}; p90 {fmt_len(qv(a['error_3d_m'], 'p90'))}; "
            f"p95 {fmt_len(qv(a['error_3d_m'], 'p95'))}; p99 {fmt_len(qv(a['error_3d_m'], 'p99'))}",
            f"  relative range error median {qv(a['range_relative'], 'median') or 0:.2e}; ≤12 mm "
            f"{fr(a['fraction_3d_within_m'], '0.012')}, ≤25 mm {fr(a['fraction_3d_within_m'], '0.025')}, ≤50 mm "
            f"{fr(a['fraction_3d_within_m'], '0.05')}",
            f"vs Position: 3-D median {fmt_len(qv(b['error_3d_m'], 'median'))}; p95 {fmt_len(qv(b['error_3d_m'], 'p95'))}; "
            f"≤12 mm {fr(b['fraction_3d_within_m'], '0.012')}",
            f"natural κ median {qv(m['natural_kappa'], 'median') or 0:.1f}; spherical triangulated "
            f"{z.gsum['counts']['triangulated_epipolar']:,} / {z.gsum['counts']['correspondences']:,}"],
            size=15, step=27)
    return img


def confidence_diagnostics(d: Data) -> Image.Image:
    W, H = 2400, 1260
    img = Image.new("RGB", (W, H), S.SURFACE)
    header(img, "Confidence diagnostics — does the primitive matcher expose useful confidence signals?",
           ["Evaluable matches stratified by quartiles of each signal (descriptive; nothing is thresholded in AB1d).",
            "Bars: median |pixel-equivalent error| (left axis, log).  Right axis 0..1: red dot = oracle top-1 "
            "fraction; green diamond = fraction within 1 px."],
           [DER, REF])
    sigs = [("peak_margin", "peak margin"), ("left_patch_std_u8", "left patch texture (std, u8)"),
            ("best_zncc", "best ZNCC"), ("peak_curvature", "peak curvature"), ("candidate_count", "candidate count")]
    pw, ph = 440, 260
    for r, z in enumerate(d.gz):
        y0 = 150 + r * 360
        gaze_tag(img, 40, y0, z)
        conf = d.ev["per_gaze"][z.g]["confidence"]
        for k, (key, label) in enumerate(sigs):
            x0 = 40 + k * (pw + 26)
            strata_panel(img, x0, y0 + 40, pw, ph, conf[key], label)
    return img


def strata_panel(img, x, y, w, h, st: dict, label: str) -> None:
    dr = ImageDraw.Draw(img)
    dr.rectangle([x, y, x + w, y + h], fill=S.WHITE)
    bins = [b for b in st["bins"] if b["count"]]
    caption(dr, x + 8, y + 6, label, size=15, bold=True)
    if not bins:
        dr.rectangle([x, y, x + w, y + h], outline=S.INK2)
        return
    px0, py0, pw, ph = x + 50, y + 34, w - 100, h - 80
    lo, hi = -3.0, 2.0

    def Y(v):
        return py0 + ph * (1 - (math.log10(max(v, 1e-3)) - lo) / (hi - lo))
    for t in (-3, -2, -1, 0, 1, 2):
        yy = py0 + ph * (1 - (t - lo) / (hi - lo))
        dr.line([px0, yy, px0 + pw, yy], fill=S.GRID, width=1)
        caption(dr, px0 - 6, yy, f"{10.0 ** t:g}", size=11, fill=S.INK2, anchor="rm")
    bw = pw / len(bins)
    for k, b in enumerate(bins):
        xx = px0 + k * bw
        if b["median_abs_px"] is not None:
            dr.rectangle([xx + 6, Y(b["median_abs_px"]), xx + bw - 6, py0 + ph], fill=S.OI_SKY)
        if b["oracle_top1"] is not None:
            yy = py0 + ph * (1 - b["oracle_top1"])
            dr.ellipse([xx + bw / 2 - 5, yy - 5, xx + bw / 2 + 5, yy + 5], fill=S.OI_VERM)
        if b["within_1px"] is not None:
            yy = py0 + ph * (1 - b["within_1px"])
            dr.polygon([(xx + bw / 2 + 14, yy - 6), (xx + bw / 2 + 20, yy), (xx + bw / 2 + 14, yy + 6),
                        (xx + bw / 2 + 8, yy)], fill=S.OI_GREEN)
        caption(dr, xx + bw / 2, py0 + ph + 4, b["stratum"], size=12, fill=S.INK2, anchor="ma")
        caption(dr, xx + bw / 2, py0 + ph + 20, f"n={b['count']:,}", size=11, fill=S.INK2, anchor="ma")
    caption(dr, px0 + pw + 8, py0, "1", size=11, fill=S.INK2)
    caption(dr, px0 + pw + 8, py0 + ph - 12, "0", size=11, fill=S.INK2)
    if st.get("edges"):
        caption(dr, x + w - 8, y + 6, "edges " + ", ".join(f"{e:.3g}" for e in st["edges"]), size=11, fill=S.INK2,
                anchor="ra")
    dr.rectangle([x, y, x + w, y + h], outline=S.INK2)


def render_all(run: Path) -> tuple[dict, Data]:
    d = Data(run)
    figs = {"overview.png": overview(d), "correspondence-error.png": correspondence_error(d),
            "cost-landscapes.png": cost_landscapes(d), "natural-reconstruction.png": natural_reconstruction(d),
            "confidence-diagnostics.png": confidence_diagnostics(d)}
    return figs, d


def visualize(run: Path, vis: Path) -> dict:
    vis.mkdir(parents=True, exist_ok=True)
    figs, d = render_all(run)
    out = {}
    for name in FIGURES:
        (vis / name).write_bytes(png_bytes(figs[name]))
        out[name] = {"sha256": sha256(vis / name), "badges": BADGES[name], "size": list(figs[name].size)}
    man = {"schema": "AB1d-visuals-manifest-v1", "figures": out, "sources": d.sources,
           "examples": {g: [{"rule": n, "core_index": i} for n, i in ex] for g, ex in d.examples.items()},
           "regenerate": ".venv/bin/python tools/active_bootstrap/ab1d_run.py visualize --run RUN --visuals VIS",
           "style": "Visual Language 1 (tools/visual_language/style.py)", "fonts": S.font_hashes(),
           "statement": NOT_STATEMENT}
    (vis / "visuals-manifest.json").write_text(json.dumps(man, indent=1, sort_keys=True) + "\n")
    print(f"[ab1d] visualize: {len(out)} figures -> {vis}")
    return man
