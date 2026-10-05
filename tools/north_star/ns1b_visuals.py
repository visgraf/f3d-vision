"""North Star-1b: the scientific visuals (Visual Language 1; deterministic PNGs).

Contract: docs/north-star/ns1b-recentered-controller-handoff-contract.md, section 20.

- ``overview.png``: A the global NS1a seed set in H0 with the selected target (NS1a FROZEN INPUT); B policy recentering
  (canonical H0 beside chart C: seed -> local (0, 0), the frozen +/-25 / +/-20 domain, the physical baseline in C,
  PHYSICAL HEAD FIXED - POLICY CHART ONLY, the selected candidate in both frames); C the first controller action (seed
  look beside the new look) or the stop reason; D the canonical-H0 target map before / after with matched vs new
  surfels and the post-action read-only state.
- ``chart-covariance.png``: identity fixtures, baseline-rotated fixtures, local decisions and mapped world decisions.
- ``first-controller-action-3d.png`` (only if an action executed): seed map, new measurement, fused map, the fixed head.

Only the NS1b run and the frozen NS1a seed maps / initialization look are read; no catalog and no name.  The drawing
primitives come from Visual Language 1 (``style``) and the accepted NS1a figure helpers (pure functions only).
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

import ns1a_visuals as NV  # noqa: E402  (accepted NS1a drawing helpers; its Data class is never used)
import ns1b_chart as CH  # noqa: E402
import ns1b_spec as SP  # noqa: E402
import style as S  # noqa: E402  (Visual Language 1, read-only)

ORA, DER, REF = SP.TRUTH_ORACLE, SP.TRUTH_DERIVED, SP.TRUTH_REFERENCE
W = NV.W
BADGES = {"overview.png": [ORA, DER], "chart-covariance.png": [ORA, DER], "first-controller-action-3d.png": [ORA, DER]}
LABELS = {"overview.png": [SP.LABEL_FROZEN, SP.LABEL_NO_NAME, SP.LABEL_FIXED_HEAD, SP.LABEL_CHART, SP.LABEL_H0,
                           SP.LABEL_ORACLE_CORR, SP.LABEL_GEOMETRY, SP.LABEL_SEGMENTATION],
          "chart-covariance.png": [SP.LABEL_CHART, SP.LABEL_H0, SP.LABEL_FIXED_HEAD],
          "first-controller-action-3d.png": [SP.LABEL_H0, SP.LABEL_FIXED_HEAD, SP.LABEL_GEOMETRY]}
MAX_POINTS = 6000
TARGET_COL, SEED_COL, NEW_COL, MATCH_COL, CAND_COL = S.OI_VERM, S.GEOM_FAR, S.OI_BLUE, S.OI_GREEN, S.OI_ORANGE


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def npz(path: Path) -> dict:
    with np.load(path, allow_pickle=False) as z:
        return {k: np.asarray(z[k]) for k in z.files}


def j(path: Path):
    return json.loads(Path(path).read_text())


class Data:
    def __init__(self, run: Path) -> None:
        self.run = run
        self.sel = j(run / "selection/target-selection.json")
        self.chart = j(run / "chart/policy-chart.json")
        self.cov = j(run / "covariance/covariance-report.json")
        self.ctx = j(run / "context/context.json")
        self.pre = j(run / "probe/pre-action-probe.json")
        self.dec = j(run / "probe/decision.json")
        self.k = int(self.sel["selected"])
        self.r = np.asarray(self.chart["R_HC"], float)
        self.g0 = np.asarray(self.chart["g0_H0"], float)
        self.seed_map = npz(run / "context/target-map-H0.npz")
        maps = npz(SP.NS1A_RUN / SP.NS1A_MAPS)
        self.ns1a_ids = sorted({int(n[1:6]) for n in maps if n.endswith("_xyz_h")})
        self.ns1a_maps = {e: np.asarray(maps[SP.map_key(e, "xyz_h")], float) for e in self.ns1a_ids}
        rank = int(self.ctx["initialization_rank"])
        self.cal0 = j(SP.NS1A_RUN / SP.ns1a_obs(rank, "acquisition", "calibration.json"))
        self.rgb0 = npz(SP.NS1A_RUN / SP.ns1a_obs(rank, "acquisition", "rgb-observation.npz"))["rgb_L"]
        self.action = self.dec["case"] == "B"
        if self.action:
            self.cal1 = j(run / f"{SP.OBS_ACQ}/calibration.json")
            self.rgb1 = npz(run / f"{SP.OBS_ACQ}/rgb-observation.npz")["rgb_L"]
            self.fus = j(run / "fusion/fusion.json")
            self.patch = npz(run / "fusion/target-patch.npz")
            self.fused = npz(run / "fusion/fused-target-map.npz")
            self.post = j(run / "post/post-action-probe.json")
            self.osum = j(run / "correspondence/oracle-summary.json")
            self.cls = npz(run / "correspondence/core-class-map.npz")["core_class"]
            self.prod = npz(run / "correspondence/oracle-correspondences.npz")
            self.ids = npz(run / "segmentation/local-identity.npz")["temporary_entity_id"]


# ------------------------------------------------------------------ helpers
def frame_tag(d: ImageDraw.ImageDraw, x: float, y: float, s: str, col=S.INK2) -> None:
    f = S.font(S.T_SMALL, True)
    w = d.textlength(s, font=f) + 16
    d.rounded_rectangle([x, y, x + w, y + 28], radius=5, fill=S.WHITE, outline=col, width=2)
    d.text((x + 8, y + 4), s, font=f, fill=col)


def sky(img: Image.Image, box, title: str, tag: str) -> tuple:
    d = ImageDraw.Draw(img)
    d.rectangle(box, fill=S.PANEL, outline=S.FAINT, width=2)
    S.text(d, (box[0] + 12, box[1] + 8), title, size=S.T_BODY, bold=True)
    frame_tag(d, box[2] - 300, box[1] + 8, tag)
    return box


def eq_xy(yaw, pitch, box, yrange=(-180.0, 180.0), prange=(-90.0, 90.0)):
    x0, y0, x1, y1 = box
    u = (np.asarray(yaw, float) - yrange[0]) / (yrange[1] - yrange[0])
    v = (prange[1] - np.asarray(pitch, float)) / (prange[1] - prange[0])
    return x0 + u * (x1 - x0), y0 + v * (y1 - y0)


def angles(xyz: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    p = np.asarray(xyz, float).reshape(-1, 3)
    return np.degrees(np.arctan2(p[:, 0], -p[:, 2])), np.degrees(np.arctan2(p[:, 1], np.hypot(p[:, 0], p[:, 2])))


def sub(n: int, m: int = MAX_POINTS) -> np.ndarray:
    return np.linspace(0, n - 1, min(n, m)).astype(int) if n else np.zeros(0, int)


def dots(d, u, v, col, r=1, box=None):
    for a, b in zip(u, v):
        if box is None or (box[0] < a < box[2] and box[1] < b < box[3]):
            d.rectangle([a - r, b - r, a + r, b + r], fill=col)


def text_block(d, x, y, lines, size=S.T_SMALL, gap=26, fill=S.INK):
    for ln in lines:
        if isinstance(ln, tuple):
            S.text(d, (x, y), ln[0], size=size, bold=True, fill=ln[1] if len(ln) > 1 else fill)
        else:
            S.text(d, (x, y), ln, size=size, fill=fill)
        y += gap
    return y


def proposal(dd: Data) -> dict | None:
    return dd.pre["probe"]["proposal"]


def new_panel(w: int, h: int, title: str, tag: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    """A panel drawn on its own image (so every mark is clipped to it), pasted by the caller."""
    im = Image.new("RGB", (w, h), S.PANEL)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w - 1, h - 1], outline=S.FAINT, width=2)
    S.text(d, (12, 8), title, size=S.T_BODY, bold=True)
    if tag:
        f = S.font(S.T_SMALL, True)
        frame_tag(d, w - d.textlength(tag, font=f) - 30, 8, tag)
    return im, d


def surfel_classes(dd: Data) -> dict:
    """After the fusion: seed surfels untouched, seed surfels matched (support >= 2) and new appended surfels."""
    n0 = len(dd.seed_map["xyz_h"])
    if not dd.action:
        return {"seed": dd.seed_map["xyz_h"], "matched": np.empty((0, 3)), "new": np.empty((0, 3))}
    f = dd.fused
    sc = np.asarray(f["support_count"])
    idx = np.arange(len(sc))
    return {"seed": f["xyz_h"][(idx < n0) & (sc <= 1)], "matched": f["xyz_h"][(idx < n0) & (sc > 1)],
            "new": f["xyz_h"][idx >= n0]}


def draw_classes(d: ImageDraw.ImageDraw, proj, cls: dict, w: int, h: int) -> None:
    box = (2, 40, w - 2, h - 2)
    a, b = proj(cls["seed"][sub(len(cls["seed"]))]) if len(cls["seed"]) else (np.empty(0), np.empty(0))
    dots(d, a, b, SEED_COL, r=1, box=box)
    if len(cls["new"]):
        a, b = proj(cls["new"][sub(len(cls["new"]))])
        dots(d, a, b, NEW_COL, r=1, box=box)
    if len(cls["matched"]):
        a, b = proj(cls["matched"][sub(len(cls["matched"]), 2500)])
        for x, y in zip(a, b):
            if box[0] < x < box[2] and box[1] < y < box[3]:
                S.xmark(d, x, y, r=3, color=MATCH_COL, width=2)


def class_legend(d: ImageDraw.ImageDraw, x: int, y: int, cls: dict) -> None:
    d.rectangle([x, y + 6, x + 8, y + 14], fill=SEED_COL)
    S.text(d, (x + 16, y), f"seed surfel, unmatched ({len(cls['seed']):,})", size=15)
    S.xmark(d, x + 4, y + 36, r=5, color=MATCH_COL, width=2)
    S.text(d, (x + 16, y + 26), f"seed surfel matched within 12 mm ({len(cls['matched']):,})", size=15)
    d.rectangle([x, y + 58, x + 8, y + 66], fill=NEW_COL)
    S.text(d, (x + 16, y + 52), f"new surfel from the action ({len(cls['new']):,})", size=15)


# ------------------------------------------------------------------ overview
def panel_a(img: Image.Image, y: int, dd: Data) -> int:
    y = NV.panel_title(img, y, "A", "Global seed set + deterministic target selection",
                       [SP.LABEL_FROZEN, SP.LABEL_NO_NAME, SP.LABEL_H0])
    d = ImageDraw.Draw(img)
    box = (40, y, 1440, y + 700)
    sky(img, box, "NS1a persistent seed maps, H0 yaw / pitch (equirectangular)", SP.LABEL_H0)
    inner = (box[0] + 20, box[1] + 50, box[2] - 20, box[3] - 20)
    for yy in range(-180, 181, 45):
        a, _ = eq_xy(yy, 0, inner)
        d.line([float(a), inner[1], float(a), inner[3]], fill=S.GRID, width=1)
        S.text(d, (float(a) - 14, inner[3] - 22), f"{yy}", size=14, fill=S.MUTED, outline=None)
    for pp in range(-90, 91, 30):
        _, b = eq_xy(0, pp, inner)
        d.line([inner[0], float(b), inner[2], float(b)], fill=S.GRID, width=1)
    for e in dd.ns1a_ids:
        xyz = dd.ns1a_maps[e]
        yaw, pitch = angles(xyz[sub(len(xyz), 2500)])
        u, v = eq_xy(yaw, pitch, inner)
        dots(d, u, v, SEED_COL if e != dd.k else TARGET_COL, r=1 if e != dd.k else 2)
        cy, cp = angles(np.median(xyz, axis=0)[None])
        a, b = eq_xy(cy, cp, inner)
        if e == dd.k:
            S.ring(d, float(a[0]), float(b[0]), r=34, color=TARGET_COL, width=4)
            S.text(d, (float(a[0]) + 38, float(b[0]) - 14), f"target {e}", size=S.T_BODY, bold=True, fill=TARGET_COL)
        else:
            S.text(d, (float(a[0]) + 6, float(b[0]) - 8), str(e), size=14, fill=S.INK2)
    ga, gb = eq_xy(*dd.sel["selected_gaze_deg"], inner)
    S.crosshair(d, float(ga), float(gb), r=18, color=TARGET_COL)
    x = 1470
    rows = [(f"Selected temporary entity id: {dd.k}", TARGET_COL),
            f"initialization gaze: rank {dd.sel['selected_rank']}  "
            f"({dd.sel['selected_gaze_deg'][0]:+.2f}, {dd.sel['selected_gaze_deg'][1]:+.2f}) deg H0",
            f"physical stereo leverage L = sqrt(1 - (b.g)^2) = {dd.sel['selected_leverage']:.4f}",
            f"single-patch provenance: {dd.ctx['map']['patch_ids']}  ({dd.ctx['map']['surfels']:,} surfels)",
            f"decided by: {dd.sel['decided_by']}", ("Candidates (initialized, 1 patch):", S.INK)]
    yy = text_block(d, x, y + 10, rows)
    for c in dd.sel["candidates"]:
        mark = "->" if c["temporary_entity_id"] == dd.k else "  "
        S.text(d, (x, yy), f"{mark} id {c['temporary_entity_id']:>4}  rank {c['initialized_at_rank']}  "
                           f"L {c['leverage']:.4f}  surfels {c['final_surfels']:>6,}", size=16,
               fill=TARGET_COL if c["temporary_entity_id"] == dd.k else S.INK2, bold=c["temporary_entity_id"] == dd.k)
        yy += 23
    ex = [e["temporary_entity_id"] for e in dd.sel["excluded"] if "patches" in e["reason"]]
    yy = text_block(d, x, yy + 8, [f"excluded (multi-patch oracle ids): {ex}",
                                   f"excluded (never initialized): {sum(1 for e in dd.sel['excluded'] if 'not' in e['reason'])}",
                                   "inputs: seed-set.json + gaze list + accepted sensor geometry only",
                                   "no object name, catalog, Controller-01 result or probe"], size=16, gap=23)
    return box[3] + 24


def panel_b(img: Image.Image, y: int, dd: Data) -> int:
    y = NV.panel_title(img, y, "B", "Policy recentering: a temporary chart, not head motion",
                       [SP.LABEL_FIXED_HEAD, SP.LABEL_CHART, SP.LABEL_H0])
    r, g0 = dd.r, dd.g0
    prop = proposal(dd)
    xyz = dd.seed_map["xyz_h"]
    # left: canonical H0 around the seed (yaw / pitch window), the chart's domain drawn in H0
    W1, H1 = 1140, 640
    left, d = new_panel(W1, H1, "Canonical H0 around the seed gaze (yaw / pitch, deg)", SP.LABEL_H0)
    sy, sp_ = dd.sel["selected_gaze_deg"]
    win = 34.0
    yr, pr = (sy - win, sy + win), (sp_ - win * 0.8, sp_ + win * 0.8)
    inner = (20, 50, W1 - 20, H1 - 70)

    def h0xy(yaw, pitch):
        yaw = (np.asarray(yaw, float) - sy + 180.0) % 360.0 - 180.0 + sy
        return eq_xy(yaw, pitch, inner, yr, pr)
    for t_ in range(-90, 91, 10):
        _, bb = h0xy(sy, t_)
        if inner[1] < float(bb) < inner[3]:
            d.line([inner[0], float(bb), inner[2], float(bb)], fill=S.GRID, width=1)
            S.text(d, (inner[0] + 2, float(bb) - 16), f"{t_}", size=13, fill=S.MUTED, outline=None)
    a, b = h0xy(*angles(xyz[sub(len(xyz))]))
    dots(d, a, b, TARGET_COL, r=1, box=inner)
    edge = [CH.local_to_world_gaze(u, v, r)[:2] for u, v in
            [(t_, -20.0) for t_ in np.linspace(-25, 25, 51)] + [(25.0, t_) for t_ in np.linspace(-20, 20, 41)]
            + [(t_, 20.0) for t_ in np.linspace(25, -25, 51)] + [(-25.0, t_) for t_ in np.linspace(20, -20, 41)]]
    ea, eb = h0xy([e[0] for e in edge], [e[1] for e in edge])
    pts = list(zip(ea.tolist(), eb.tolist()))
    for p0, p1 in zip(pts, pts[1:]):
        if abs(p0[0] - p1[0]) < W1 / 3:                     # skip the yaw seam
            S.dashed_line(d, [p0, p1], CAND_COL, width=3, dash=10, gap=7)
    ca, cb = h0xy(sy, sp_)
    S.crosshair(d, float(ca), float(cb), r=16, color=S.INK)
    S.text(d, (float(ca) + 18, float(cb) + 6), "seed gaze g0 (H0)", size=16, bold=True)
    if prop:
        pa, pb = h0xy(*prop["world_gaze_deg"])
        S.arrow(d, float(ca), float(cb), float(pa), float(pb), color=NEW_COL, width=4, head=16)
        S.ring(d, float(pa), float(pb), r=10, color=NEW_COL, width=3)
        S.text(d, (float(pa) + 14, float(pb) - 30), f"world gaze ({prop['world_gaze_deg'][0]:+.2f}, "
                                                    f"{prop['world_gaze_deg'][1]:+.2f})", size=16, bold=True,
               fill=NEW_COL)
    S.text(d, (14, H1 - 60), "dashed: the frozen +/-25 / +/-20 local domain of chart C, mapped into H0", size=15,
           fill=S.INK2)
    S.text(d, (14, H1 - 34), f"chart up (y_C) . world up = {dd.chart['chart_up_dot_world_up']:+.3f}; local +yaw "
                             "points along the projected physical baseline (+X)", size=15, fill=S.INK2)
    img.paste(left, (40, y))
    # right: chart C
    W2, H2 = 1150, 640
    right, d = new_panel(W2, H2, "Policy chart C (local yaw / pitch, deg)", SP.LABEL_CHART)
    ci = (20, 50, W2 - 20, H2 - 70)
    lim = (-34.0, 34.0), (-27.0, 27.0)
    lc = SP.SURFACE_FRONTIER

    def cxy(yaw, pitch):
        return eq_xy(yaw, pitch, ci, lim[0], lim[1])
    for t_ in range(-30, 31, 5):
        a1, _ = cxy(t_, 0)
        d.line([float(a1), ci[1], float(a1), ci[3]], fill=S.GRID, width=1)
        if -26 < t_ < 26:
            _, b1 = cxy(0, t_)
            d.line([ci[0], float(b1), ci[2], float(b1)], fill=S.GRID, width=1)
    q0, q1 = cxy(lc["yaw_min_deg"], lc["pitch_max_deg"]), cxy(lc["yaw_max_deg"], lc["pitch_min_deg"])
    S.dashed_rect(d, [float(q0[0]), float(q0[1]), float(q1[0]), float(q1[1])], CAND_COL, width=3)
    S.text(d, (float(q0[0]) + 6, float(q0[1]) + 4), "frozen FSG6f domain: yaw +/-25, pitch +/-20, 5 deg step",
           size=15, fill=CAND_COL, bold=True)
    a, b = cxy(*angles(CH.to_chart(xyz[sub(len(xyz))], r)))
    dots(d, a, b, TARGET_COL, r=1, box=ci)
    o = cxy(0.0, 0.0)
    S.crosshair(d, float(o[0]), float(o[1]), r=16, color=S.INK)
    S.text(d, (float(o[0]) + 18, float(o[1]) + 6), "g0 -> local (0, 0)", size=16, bold=True)
    for cand in (dd.pre["probe"]["decisions"].get("fsg6f_decision") or {}).get("candidates", []):
        a1, b1 = cxy(cand["yaw_deg"], cand["pitch_deg"])
        S.square(d, float(a1), float(b1), r=6, color=CAND_COL)
    if prop:
        pa, pb = cxy(*prop["local_gaze_deg"])
        S.arrow(d, float(o[0]), float(o[1]), float(pa), float(pb), color=NEW_COL, width=4, head=16)
        S.ring(d, float(pa), float(pb), r=10, color=NEW_COL, width=3)
        S.text(d, (float(pa) + 14, float(pb) + 10), f"selected ({prop['local_gaze_deg'][0]:+.1f}, "
                                                    f"{prop['local_gaze_deg'][1]:+.1f}) {prop['source']}",
               size=16, bold=True, fill=NEW_COL)
    bc = np.asarray(dd.chart["checks"]["baseline_in_C"])
    S.arrow(d, W2 - 200, H2 - 100, W2 - 200 + 120 * bc[0], H2 - 100 - 120 * bc[1], color=S.INK2, width=3, head=12)
    S.text(d, (W2 - 560, H2 - 60), f"physical baseline in C = ({bc[0]:+.3f}, {bc[1]:+.3f}, {bc[2]:+.3f})",
           size=15, fill=S.INK2)
    S.text(d, (14, H2 - 34), "squares: FSG6f candidates surviving consensus + continuation", size=15, fill=S.INK2)
    img.paste(right, (1210, y))
    d = ImageDraw.Draw(img)
    yy = y + H1 + 12
    S.text(d, (40, yy), "R_HC (rows of the matrix; columns are x_C, y_C, z_C in H0): " + "  ".join(
        "[" + ", ".join(f"{v:+.4f}" for v in row) + "]" for row in np.asarray(dd.chart["R_HC"])), size=16,
        fill=S.INK2)
    S.text(d, (40, yy + 26), "PHYSICAL HEAD FIXED: eye centres (-/+0.0315, 0, 0) m in H0 for every calibration; "
                             "chart C carries policy geometry only; persistent geometry stays in H0", size=16,
           bold=True)
    return yy + 66


def panel_c(img: Image.Image, y: int, dd: Data) -> int:
    y = NV.panel_title(img, y, "C", "First controller action" if dd.action else "Pre-action decision (no action)",
                       [SP.LABEL_ORACLE_CORR, SP.LABEL_GEOMETRY, SP.LABEL_SEGMENTATION])
    d = ImageDraw.Draw(img)
    size = 420
    img.paste(NV.core_rgb_tile(dd.rgb0, size), (40, y + 34))
    S.text(d, (40, y), f"seed look: NS1a rank {dd.ctx['initialization_rank']} (reused, no rerender)",
           size=16, bold=True)
    S.text(d, (40, y + 460), f"H0 gaze ({dd.cal0['gaze_yaw_pitch_deg'][0]:+.2f}, "
                             f"{dd.cal0['gaze_yaw_pitch_deg'][1]:+.2f}); local (0, 0)", size=16)
    p = dd.pre["probe"]
    f = p["summary"]["fsg6f"]
    lines = [("Pre-action probe (read-only, once)", S.INK),
             f"FSG6f: {f['reason']}; frontier raw {f['frontier_raw_count']} / open {f['frontier_open_count']} / "
             f"map {f['frontier_map_resolved_count']} / boundary {f['frontier_boundary_resolved_count']}",
             f"candidates {f['candidates']}; consensus-rejected {f['consensus_rejected_candidates']}"]
    cyc = p["summary"].get("cyclopean")
    if cyc:
        lines.append(f"Cyclopean: {cyc['reason']}; eligible cells {cyc['eligible_cells']}")
    g = p["gate"]
    counts = g["detail"].get("counts") or {}
    lines += [f"Controller-02 gate v1: {'ADMISSIBLE' if g['admissible'] else 'REJECTED'} ({g['reason']})",
              f"support {counts.get('support', '-')}, in both predicted cores {counts.get('in_both_cores', '-')}, "
              f"novel serviceable {counts.get('novel_service_count', '-')}"]
    prop = proposal(dd)
    if prop:
        lines += [f"local gaze ({prop['local_gaze_deg'][0]:+.1f}, {prop['local_gaze_deg'][1]:+.1f}) -> H0 "
                  f"({prop['world_gaze_deg'][0]:+.3f}, {prop['world_gaze_deg'][1]:+.3f})",
                  f"{prop['angle_from_seed_deg']:.2f} deg from the seed; leverage {prop['leverage']:.4f}"]
    lines.append((f"decision: {dd.dec['outcome_reading']}", NEW_COL if dd.action else S.INK))
    text_block(d, 490, y + 40, lines, size=17, gap=27)
    if not dd.action:
        return y + 520
    img.paste(NV.core_rgb_tile(dd.rgb1, size), (1480, y + 34))
    S.text(d, (1480, y), "the ONE new fixed-head observation (4096 spp)", size=16, bold=True)
    S.text(d, (1480, y + 460), f"H0 gaze ({dd.cal1['gaze_yaw_pitch_deg'][0]:+.3f}, "
                               f"{dd.cal1['gaze_yaw_pitch_deg'][1]:+.3f})", size=16)
    tile = Image.new("RGB", (256, 256), NV.NO_HIT_BG)
    t = np.array(tile)
    t[dd.cls == 1] = NV.UNASSIGNED_BG
    t[dd.cls == 2] = NV.NOTVIS_BG
    rows, cols = dd.prod["left_core_row"], dd.prod["left_core_col"]
    ids = dd.ids
    t[rows[ids > 0], cols[ids > 0]] = (170, 170, 170)
    t[rows[ids == dd.k], cols[ids == dd.k]] = TARGET_COL
    tile = Image.fromarray(t).resize((size, size), Image.NEAREST)
    img.paste(tile, (1920, y + 34))
    NV.class_overlays(img, dd.cls, 1920, y + 34, size)
    d = ImageDraw.Draw(img)
    S.text(d, (1920, y), f"correspondences: target {dd.k} vs other ids", size=16, bold=True)
    S.text(d, (1920, y + 460), f"{dd.osum['correspondences']:,} PERFECT; target points "
                               f"{dd.fus['measured_points']:,}", size=16)
    return y + 520


def chart_view_proj(dd: Data, w: int, h: int, pts: np.ndarray):
    """Orthographic view along the seed gaze: display axes x_C / y_C, positions in canonical-H0 metres."""
    cen = np.median(dd.seed_map["xyz_h"], axis=0)
    q = (np.asarray(pts, float) - cen) @ dd.r
    ext = float(np.percentile(np.abs(q[:, :2]), 99.5)) * 1.12 + 1e-3
    s = (min(w, h - 60) / 2 - 20) / ext
    cx, cy = w / 2, (h + 40) / 2

    def proj(p):
        qq = (np.asarray(p, float).reshape(-1, 3) - cen) @ dd.r
        return cx + s * qq[:, 0], cy - s * qq[:, 1]
    return proj, s


def scale_bar(d, x, y, s, metres=0.1):
    d.line([x, y, x + s * metres, y], fill=S.INK, width=3)
    S.text(d, (x, y + 4), f"{metres * 100:.0f} cm", size=14, fill=S.INK2)


def panel_d(img: Image.Image, y: int, dd: Data) -> int:
    y = NV.panel_title(img, y, "D", "Persistent map consequence (canonical H0)" if dd.action else
                       "Persistent map (canonical H0, unchanged)", [SP.LABEL_H0, SP.LABEL_GEOMETRY])
    seed = dd.seed_map["xyz_h"]
    cls = surfel_classes(dd)
    allp = np.vstack([seed, cls["new"]]) if len(cls["new"]) else seed
    w, h = 790, 560
    for i, title in enumerate(("before: NS1a seed map", "after: one H0 fusion (12 mm / 12 mm)")):
        im, d = new_panel(w, h, title, SP.LABEL_H0)
        proj, s = chart_view_proj(dd, w, h, allp)
        if i == 0:
            a, b = proj(seed[sub(len(seed))])
            dots(d, a, b, SEED_COL, r=1, box=(2, 40, w - 2, h - 2))
            n = len(seed)
        else:
            draw_classes(d, proj, cls, w, h)
            n = sum(len(v) for v in cls.values())
        scale_bar(d, 20, h - 50, s)
        S.text(d, (w - 230, h - 34), f"{n:,} surfels", size=16, bold=True)
        img.paste(im, (40 + i * 820, y))
    d = ImageDraw.Draw(img)
    x = 1700
    if dd.action:
        fu = dd.fus
        md = fu.get("matched_distance_m") or {}
        rows = [(f"12-mm fusion: {fu['action']}", NEW_COL),
                f"map before {fu['map_before']:,}", f"measured target points {fu['measured_points']:,}",
                f"matched existing surfels {fu['matched']:,}", f"new surfels {fu['new']:,}",
                f"affected surfels {fu['affected_surfels']:,}",
                "matched distance median / p95 / max:", ("  " + (f"{md['median'] * 1000:.2f} / {md['p95'] * 1000:.2f} / "
                                                                 f"{md['max'] * 1000:.2f} mm" if md else "none"), S.INK),
                f"map after {fu['map_after']:,}",
                "replay: idempotent (exact)" if fu.get("replay", {}).get("exact") else "replay: not fused"]
        po = dd.post["probe"]
        pp = po["proposal"]
        rows += [("Post-action probe (read-only; NOT executed)", S.INK), f"state {po['state']}",
                 "proposal: none" if pp is None else f"proposal {pp['source']}",
                 "" if pp is None else f"  local ({pp['local_gaze_deg'][0]:+.1f}, {pp['local_gaze_deg'][1]:+.1f})",
                 f"gate: {po['gate']['reason']}"]
    else:
        rows = [("No action executed", S.INK), f"map unchanged: {len(seed):,} surfels",
                f"reason: {dd.dec['outcome_reading']}"]
    yy = text_block(d, x, y + 10, [r_ for r_ in rows if r_], size=17, gap=28)
    class_legend(d, x, yy + 6, cls)
    S.text(d, (40, y + h + 8), "view along the seed gaze: display axes x_C / y_C of chart C; positions are "
                               "canonical-H0 metres; the fusion itself ran in H0", size=15, fill=S.INK2)
    return y + h + 44


def overview(dd: Data) -> tuple[Image.Image, dict]:
    img = Image.new("RGB", (W, 3600), S.SURFACE)
    y = NV.header(img, f"North Star-1b - recentered local-controller handoff, one action (target {dd.k})",
                  ["A frozen NS1a seed is handed to the accepted FSG6f -> Cyclopean / Controller-02 semantics through a "
                   "TEMPORARY POLICY COORDINATE CHART.",
                   "The physical head does not move: every projection, calibration and observation stays in canonical "
                   "H0; persistent fusion happens in H0."], BADGES["overview.png"])
    y = panel_a(img, y + 10, dd)
    y = panel_b(img, y, dd)
    y = panel_c(img, y, dd)
    y = panel_d(img, y, dd)
    img = img.crop((0, 0, W, y + 20))
    return img, {"panels": ["A", "B", "C", "D"], "action": dd.action}


# ------------------------------------------------------------------ chart covariance
def covariance_fig(dd: Data) -> tuple[Image.Image, dict]:
    img = Image.new("RGB", (W, 1500), S.SURFACE)
    y = NV.header(img, "North Star-1b - chart covariance (established before the adapter touched NS1a data)",
                  ["Identity chart: the adapter reproduces the accepted policy exactly. Rotation about the physical "
                   "baseline (the fixed head's exact symmetry): the same local decision, rotated world decision."],
                  BADGES["chart-covariance.png"])
    d = ImageDraw.Draw(img)
    cov = dd.cov
    an, rp = cov["analytic"], cov["replay"]
    y = NV.panel_title(img, y + 10, "1", "Identity chart (R_HC = I) and accepted known answers", [SP.LABEL_CHART,
                                                                                                    SP.LABEL_H0])
    rows = []
    for c in an["K1_fsg6f"]["cases"]:
        rows.append(f"K1 FSG6f {c['name']}: next {c['next_gaze_deg']} ({c['reason']}); identity "
                    f"{'EXACT' if not c['identity_differences'] else 'DIFF'}; known answer {c['known_answer']}")
    rows.append(f"K1 Cyclopean bay: fixation {an['K1_cyclopean']['bay']['next_gaze_deg']}; identity "
                f"{an['K1_cyclopean']['bay']['identity_equal']}")
    rows.append(f"K1 gate: {an['K1_gate']['verdict']}; identity differences {len(an['K1_gate']['identity_differences'])}")
    for k in ("K2", "K3", "K3q"):
        r = rp[k]
        rows.append(f"{k} object {r['object']} after step {r['after_global_step']} (revision {r['revision']}): {r['state']}"
                    f" - accepted record reproduced {'EXACTLY' if not r['differences_from_accepted_record'] else 'NO'}")
    k4 = rp["K4"]
    rows.append(f"K4 object 210 Controller-02 gate: {k4['verdict']} - accepted verdict reproduced "
                f"{'EXACTLY' if not k4['differences_from_accepted_record'] else 'NO'} (support {k4['counts']['support']}, "
                f"in both cores {k4['counts']['in_both_cores']})")
    y = text_block(d, 50, y, rows, size=16, gap=24) + 10
    y = NV.panel_title(img, y, "2", "Rigid rotation about the physical baseline: local decision unchanged",
                       [SP.LABEL_FIXED_HEAD])
    # a small drawing per rotation: the analytic fixture a, original chart decision and the rotated world decision
    case = next(c for c in an["K1_fsg6f"]["cases"] if c["name"] == "a_map_lower_left")
    bw = 560
    for i, rot in enumerate(an["K1_fsg6f"]["rotations"]):
        bx = (40 + i * (bw + 20), y, 40 + i * (bw + 20) + bw, y + 420)
        d.rectangle(bx, fill=S.PANEL, outline=S.FAINT, width=2)
        beta = rot["beta_deg"]
        S.text(d, (bx[0] + 10, bx[1] + 8), f"beta = {beta:+.0f} deg about +X", size=S.T_BODY, bold=True)
        cx, cy = (bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2 + 20
        s = 7.0
        q = CH.rot_x(beta)
        # world (H0) directions: the original proposal and the rotated one, drawn in the YZ plane (side view)
        d0 = CH.gaze_direction(*case["next_gaze_deg"])
        for vec, col, lab in ((np.array([0, 0, -1.0]), S.MUTED, "seed"), (d0, S.INK2, "original"),
                              (q @ np.array([0, 0, -1.0]), TARGET_COL, "rotated seed"), (q @ d0, NEW_COL, "rotated")):
            ex, ey = cx + s * 22 * (-vec[2]), cy - s * 22 * vec[1]
            S.arrow(d, cx, cy, ex, ey, color=col, width=3, head=12)
            S.text(d, (ex + 4, ey - 10), lab, size=14, fill=col)
        diffs = sum(len(c["differences"]) for c in rot["cases"])
        inv = sum(len(c["tie_inversions"]) for c in rot["cases"])
        flips = sum(1 for c in rot["cases"] if c["voxel_boundary_flip"])
        S.text(d, (bx[0] + 10, bx[3] - 84), f"8 fixtures: local differences {diffs}", size=15, bold=True)
        S.text(d, (bx[0] + 10, bx[3] - 60), f"float tie inversions {inv}; voxel-boundary flips {flips}", size=15)
        S.text(d, (bx[0] + 10, bx[3] - 36), "side view (H0 -Z right, +Y up)", size=14, fill=S.MUTED)
    by = (40 + 3 * (bw + 20), y, W - 40, y + 420)
    d.rectangle(by, fill=S.PANEL, outline=S.FAINT, width=2)
    rows = [("Accepted replay states", S.INK)]
    for k in ("K2", "K3", "K3q"):
        rr = rp[k]
        rows.append(f"{k}: " + ", ".join(f"{x['beta_deg']:+.0f}: {len(x['differences'])} diff" for x in rr["rotations"]))
    rows.append(("This NS1b seed (in the probe)", S.INK))
    for x in dd.pre["baseline_rotation_invariance"]:
        rows.append(f"{x['beta_deg']:+.0f} deg: {'equal' if x['pass'] else 'DIFFERENT'}; world error "
                    f"{x.get('world_proposal_error', 0.0):.1e}")
    text_block(d, by[0] + 10, by[1] + 10, rows, size=15, gap=24)
    y = by[3] + 20
    y = NV.panel_title(img, y, "3", "Projection invariance and the physical sensor", [SP.LABEL_H0])
    pc = cov["projection_invariance_canonical_chart"]
    rows = [f"canonical chart: max |uv(C->H0) - uv(H0)| = {max(r['uv_difference_px'] for r in pc['rows']):.1e} px; "
            f"negative control (C point projected as if H0) >= {min(r['negative_control_px'] for r in pc['rows']):.0f} px",
            f"Controller-02 predicted calibration (P3) = the real fixed-head sensor at the WORLD gaze; the fake local "
            f"calibration is refused (synthetic 11, 15)",
            f"adapter substitutions: P1 FSG6f projection, P2 Cyclopean directions, P3 predicted calibration; all restored"]
    y = text_block(d, 50, y, rows, size=16, gap=26)
    img = img.crop((0, 0, W, y + 20))
    return img, {"rotations": [r["beta_deg"] for r in an["K1_fsg6f"]["rotations"]]}


# ------------------------------------------------------------------ 3-D action figure
def action_3d(dd: Data) -> tuple[Image.Image, dict]:
    img = Image.new("RGB", (W, 1900), S.SURFACE)
    y = NV.header(img, f"North Star-1b - first controller action in canonical H0 (target {dd.k})",
                  ["Seed map, the new PERFECT spherical measurement of the target and the fused map; the fixed head at "
                   "the H0 origin with its baseline on +X (eye centres -/+0.0315 m)."],
                  BADGES["first-controller-action-3d.png"])
    seed, new = dd.seed_map["xyz_h"], np.asarray(dd.patch["xyz_h"])
    cls = surfel_classes(dd)
    allp = np.vstack([seed, new, np.zeros((1, 3))]) if len(new) else np.vstack([seed, np.zeros((1, 3))])
    views = (("top (X right, -Z up)", lambda p: (p[:, 0], -p[:, 2])), ("front (X right, Y up)", lambda p: (p[:, 0], p[:, 1])),
             ("side (-Z right, Y up)", lambda p: (-p[:, 2], p[:, 1])))
    bw, bh = 760, 760
    g1 = CH.gaze_direction(*dd.cal1["gaze_yaw_pitch_deg"])
    rng = float(np.median(np.linalg.norm(seed, axis=1)))
    for i, (title, f) in enumerate(views):
        im, d = new_panel(bw, bh, title, SP.LABEL_H0)
        u, v = f(allp)
        umin, umax, vmin, vmax = u.min(), u.max(), v.min(), v.max()
        s = min((bw - 120) / max(1e-6, umax - umin), (bh - 160) / max(1e-6, vmax - vmin))
        ox = (bw - s * (umax - umin)) / 2 - s * umin
        oy = bh - (bh - 40 - s * (vmax - vmin)) / 2 + s * vmin

        def xy(p, f=f, s=s, ox=ox, oy=oy):
            a, b = f(np.asarray(p, float).reshape(-1, 3))
            return ox + s * a, oy - s * b
        hx, hy = xy(np.zeros((1, 3)))
        for g, col, lab in ((dd.g0, S.INK2, "seed gaze"), (g1, NEW_COL, "action gaze")):
            ex, ey = xy(g[None] * rng)
            S.dashed_line(d, [(float(hx[0]), float(hy[0])), (float(ex[0]), float(ey[0]))], col, width=2)
        draw_classes(d, xy, cls, bw, bh)
        el, er = xy(np.array([[-0.0315, 0, 0]])), xy(np.array([[0.0315, 0, 0]]))
        d.line([float(el[0][0]) - 6, float(el[1][0]), float(er[0][0]) + 6, float(er[1][0])], fill=S.INK, width=6)
        d.ellipse([float(hx[0]) - 5, float(hy[0]) - 5, float(hx[0]) + 5, float(hy[0]) + 5], outline=S.INK, width=2)
        S.text(d, (14, bh - 34), "fixed head: H0 origin, baseline on +X", size=15, bold=True)
        img.paste(im, (40 + i * (bw + 20), y + 10))
    # zoomed view along the seed gaze
    zy = y + 10 + bh + 20
    zw, zh = 1500, 780
    im, d = new_panel(zw, zh, "zoom: the target map viewed along the seed gaze (axes x_C / y_C; H0 metres)",
                      SP.LABEL_H0)
    proj, s = chart_view_proj(dd, zw, zh, np.vstack([seed, new]) if len(new) else seed)
    draw_classes(d, proj, cls, zw, zh)
    scale_bar(d, 20, zh - 40, s)
    img.paste(im, (40, zy))
    d = ImageDraw.Draw(img)
    fu = dd.fus
    md = fu.get("matched_distance_m") or {}
    rows = [("12-mm fusion in canonical H0", NEW_COL), f"seed {fu['map_before']:,} surfels",
            f"measured target points {fu['measured_points']:,}", f"matched {fu['matched']:,} -> affected surfels "
                                                                 f"{fu['affected_surfels']:,}",
            f"new {fu['new']:,}", f"fused {fu['map_after']:,} surfels",
            "matched distance median / p95 / max:" if md else "no matched distances",
            ("  " + f"{md['median'] * 1000:.2f} / {md['p95'] * 1000:.2f} / {md['max'] * 1000:.2f} mm", S.INK) if md
            else "", "replay idempotent (exact)" if fu.get("replay", {}).get("exact") else ""]
    yy = text_block(d, 1580, zy + 20, [r_ for r_ in rows if r_], size=17, gap=30)
    class_legend(d, 1580, yy + 10, cls)
    img = img.crop((0, 0, W, zy + zh + 20))
    return img, {"views": [v[0] for v in views] + ["zoom along the seed gaze"]}


def render_all(run: Path) -> tuple[dict, Data]:
    dd = Data(run)
    figs = {"overview.png": overview, "chart-covariance.png": covariance_fig}
    if dd.action:
        figs[SP.FIGURE_ACTION] = action_3d
    return {n: fn(dd) for n, fn in figs.items()}, dd


def visualize(run: Path, vis: Path) -> dict:
    vis = Path(vis)
    vis.mkdir(parents=True, exist_ok=True)
    figs, dd = render_all(run)
    man = {"schema": "NS1b-visuals-v1", "visual_language": "Visual Language 1", "run": str(run),
           "font_hashes": S.font_hashes(), "figures": {}, "frames": {"chart": SP.LABEL_CHART, "h0": SP.LABEL_H0},
           "fixed_head_statement": SP.LABEL_FIXED_HEAD, "action_executed": dd.action}
    for name, (im, meta) in figs.items():
        path = vis / name
        im.save(path, format="PNG", optimize=False)
        man["figures"][name] = {"sha256": sha256(path), "size": list(im.size), "badges": BADGES[name],
                                "labels": LABELS[name], **meta}
    (vis / "visuals-manifest.json").write_text(json.dumps(man, indent=1, sort_keys=True) + "\n")
    return man
