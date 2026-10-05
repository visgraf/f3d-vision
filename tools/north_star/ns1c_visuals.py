"""North Star-1c: the scientific visuals (Visual Language 1; deterministic PNGs).

Contract: docs/north-star/ns1c-coherent-first-scene-switch-contract.md, section 25.

- ``overview.png``: A North-Star scene state (coarse 360 RGB in H0; the coherent seed maps; 172 current; the deferred
  identities apart); B the initial service map; C the attention timeline (the first switch prominent); D the first
  cross-entity action; E the scene state after the switch (the new target's next proposal NOT EXECUTED).
- ``scene-scheduler-timeline.png``: rows entities, columns global actions; service states, current target, transitions.
- ``multi-entity-growth-3d.png``: canonical-H0 geometry of 172 and of the second entity before / after their actions.
- ``controller-vs-northstar-support.png``: descriptive; controller-state target support vs North-Star target points.

Only the NS1c run, the frozen NS1a maps of the deferred identities (display only) and the RGB-only coarse 360 backdrop
are read; no catalog and no name.  Drawing primitives: Visual Language 1 (``style``) and the accepted NS1a / NS1b figure
helpers (pure functions only).
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
import ns1b_visuals as BV  # noqa: E402  (accepted NS1b drawing helpers; its Data class is never used)
import ns1c_core as CORE  # noqa: E402
import ns1c_spec as SP  # noqa: E402
import style as S  # noqa: E402  (Visual Language 1, read-only)

ORA, DER = SP.TRUTH_ORACLE, SP.TRUTH_DERIVED
W = NV.W
BADGES = {"overview.png": [ORA, DER], "scene-scheduler-timeline.png": [DER],
          "multi-entity-growth-3d.png": [ORA, DER], "controller-vs-northstar-support.png": [ORA, DER]}
LABELS = {"overview.png": [SP.LABEL_FROZEN, SP.LABEL_NO_NAME, SP.LABEL_FIXED_HEAD, SP.LABEL_CHART, SP.LABEL_H0,
                           SP.LABEL_DEFERRED, SP.LABEL_SCHEDULER, SP.LABEL_NOT_EXECUTED, SP.LABEL_ORACLE_CORR,
                           SP.LABEL_GEOMETRY, SP.LABEL_SEGMENTATION],
          "scene-scheduler-timeline.png": [SP.LABEL_SCHEDULER, SP.LABEL_DEFERRED],
          "multi-entity-growth-3d.png": [SP.LABEL_H0, SP.LABEL_FIXED_HEAD, SP.LABEL_GEOMETRY],
          "controller-vs-northstar-support.png": [SP.LABEL_ORACLE_CORR, SP.LABEL_GEOMETRY]}
CUR_COL, NEW_COL, SEED_COL, DEF_COL = S.OI_VERM, S.OI_BLUE, S.GEOM_FAR, (150, 150, 150)
PALETTE = [S.OI_GREEN, S.OI_ORANGE, S.OI_PURPLE, S.OI_SKY, S.WINE, S.REF_BROWN, (90, 90, 90), (0, 90, 140),
           (160, 120, 0), (110, 60, 140)]
STEP_COLS = [S.OI_BLUE, S.OI_GREEN, S.OI_ORANGE, S.OI_PURPLE, S.OI_SKY, S.WINE, S.REF_BROWN, (0, 90, 140)]

j, npz, sub, dots, angles, eq_xy, text_block, new_panel, scale_bar = (BV.j, BV.npz, BV.sub, BV.dots, BV.angles,
                                                                     BV.eq_xy, BV.text_block, BV.new_panel,
                                                                     BV.scale_bar)


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Data:
    def __init__(self, run: Path) -> None:
        self.run = Path(run)
        self.el = j(run / "eligibility/coherent-seed-set.json")
        self.charts = j(run / "charts/policy-charts.json")["charts"]
        self.ctx = j(run / "contexts/contexts.json")
        self.table = j(run / "initial-probe/initial-service-table.json")
        self.s0 = j(run / SP.scene_state_rel("initial"))
        afters = sorted((run / "scene").glob("state-after-step-*.json"))
        self.states = [self.s0] + [j(p) for p in afters]
        self.steps = []
        for st in self.states[1:]:
            k = int(st["global_step"])
            sd = run / SP.step_dir(k)
            self.steps.append({"k": k, "dec": j(sd / "plan/decision.json"), "fus": j(sd / "fusion/fusion.json"),
                               "upd": j(sd / "update/update.json"), "after": st, "sd": sd,
                               "osum": j(sd / "correspondence/oracle-summary.json")})
        self.terminal = j(run / "scene/terminal.json") if (run / "scene/terminal.json").exists() else None
        self.final = j(run / "scene/final-scene-state.json") if (run / "scene/final-scene-state.json").exists() else None
        self.ids = [int(k) for k in self.s0["scene_ids"]]
        self.deferred = [int(r["temporary_entity_id"]) for r in self.s0["deferred"]]
        self.color = {k: (CUR_COL if k == SP.CONTINUING else PALETTE[i % len(PALETTE)])
                      for i, k in enumerate(self.ids)}
        self.switch = next((s for s in self.steps if int(s["dec"]["action"]["target"]) != SP.CONTINUING), None)
        if self.switch is not None:
            self.color[int(self.switch["dec"]["action"]["target"])] = NEW_COL
        self.pano = npz(SP.NB1A_RGB[0])["srgb8"]
        maps = npz(SP.NS1A_RUN / SP.NS1A_MAPS)
        self.deferred_maps = {k: np.asarray(maps[SP.map_key(k, "xyz_h")], float) for k in self.deferred
                              if SP.map_key(k, "xyz_h") in maps}
        self.last = self.states[-1]

    def map_of(self, rec: dict) -> np.ndarray:
        return np.asarray(CORE.load_npz(CORE.resolve(rec["map"]["path"], self.run))["xyz_h"], float)

    def outcome(self) -> str:
        if self.switch is not None:
            before = self.states[self.steps.index(self.switch)]["entities"][str(SP.CONTINUING)]["service"]["label"]
            kind = ("natural scene switch (172 QUIET)" if before == "QUIET" else
                    "watchdog-driven switch (172 BLOCKED:watchdog)" if before.startswith("BLOCKED") else "switch")
            if self.switch["fus"]["action"] != "FUSED":
                return f"{kind}; the second-entity action was retained, not fused (reading left to Luiz / Chat)"
            return ("Outcome 1 - " if before == "QUIET" else "Outcome 2 - " if before.startswith("BLOCKED") else "") + kind
        if self.terminal is not None:
            return self.terminal.get("outcome_reading", "terminal")
        return "no cross-entity action"


# ------------------------------------------------------------------ helpers
def tile(img: Image.Image, box, label: str, text: str = "") -> None:
    """A service-state tile: VL1 tiles for ACTIONABLE / QUIET; BLOCKED and DEFERRED drawn with their own cues."""
    d = ImageDraw.Draw(img)
    if label in ("ACTIONABLE", "QUIET"):
        S.state_tile(img, box, label, text, size=S.T_SMALL)
        return
    x0, y0, x1, y1 = box
    if label.startswith("BLOCKED"):
        d.rectangle(box, fill=(250, 232, 220))
        d.rectangle(box, outline=S.OI_VERM, width=3)
        d.rectangle([x0 + 5, y0 + 5, x1 - 5, y1 - 5], outline=S.OI_VERM, width=2)
        g = "W"
    else:                                                    # DEFERRED_AMBIGUOUS_ORACLE_IDENTITY
        d.rectangle(box, fill=(238, 238, 238))
        S.hatch(img, box, (190, 190, 190), spacing=9, width=2, cross=True)
        d = ImageDraw.Draw(img)
        S.dashed_rect(d, box, S.INK2, width=2)
        g = "ID?"
    if text:
        f = S.font(S.T_SMALL, True)
        tw = d.textlength(text, font=f)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        tb = d.textbbox((cx - tw / 2, cy - S.T_SMALL / 2 - 2), text, font=f)
        d.rectangle([tb[0] - 3, tb[1] - 1, tb[2] + 3, tb[3] + 2], fill=S.WHITE)
        d.text((cx - tw / 2, cy - S.T_SMALL / 2 - 2), text, font=f, fill=S.INK)
    gf = S.font(16, True)
    gw = d.textlength(g, font=gf)
    d.rectangle([x1 - gw - 10, y0 + 3, x1 - 3, y0 + 23], fill=S.WHITE)
    d.text((x1 - gw - 7, y0 + 3), g, font=gf, fill=S.INK)


def fmt(v, nd=1) -> str:
    return "-" if v is None else f"({v[0]:+.{nd}f}, {v[1]:+.{nd}f})"


# ------------------------------------------------------------------ overview
def panel_a(img: Image.Image, y: int, dd: Data) -> int:
    y = NV.panel_title(img, y, "A", "North-Star scene state: the coherent seed maps in canonical H0",
                       [SP.LABEL_FROZEN, SP.LABEL_H0, SP.LABEL_NO_NAME])
    pw, ph = 1800, 900
    pano = Image.fromarray(dd.pano).resize((pw, ph), Image.BICUBIC)
    pano = Image.blend(pano, Image.new("RGB", (pw, ph), S.WHITE), 0.45)
    d = ImageDraw.Draw(pano)
    for k, xyz in sorted(dd.deferred_maps.items()):
        yaw, pitch = angles(xyz[sub(len(xyz), 900)])
        for a, b in zip(*NV.pano_xy(yaw, pitch, pw, ph)):
            S.xmark(d, float(a), float(b), r=2, color=DEF_COL, width=1)
        cy, cp = angles(np.median(xyz, axis=0)[None])
        a, b = NV.pano_xy(float(cy[0]), float(cp[0]), pw, ph)
        S.text(d, (a + 8, b - 10), f"{k} (deferred)", size=15, fill=S.INK2, plate=(236, 236, 236))
    rec0 = dd.s0["entities"]
    placed = []
    for k in dd.ids:
        xyz = dd.map_of(rec0[str(k)])
        yaw, pitch = angles(xyz[sub(len(xyz), 2500)])
        u, v = NV.pano_xy(yaw, pitch, pw, ph)
        dots(d, u, v, dd.color[k], r=2 if k == SP.CONTINUING else 1)
        cy, cp = angles(np.median(xyz, axis=0)[None])
        a, b = NV.pano_xy(float(cy[0]), float(cp[0]), pw, ph)
        lx, ly = NV.place_label(a + 10, b - 12, 60, 22, placed, (0, 0, pw, ph))
        S.text(d, (lx, ly), str(k), size=16, bold=True, fill=dd.color[k])
    c = dd.charts[str(SP.CONTINUING)]["seed_gaze_H0_deg"] if str(SP.CONTINUING) in dd.charts else None
    if c:
        a, b = NV.pano_xy(c[0], c[1], pw, ph)
        S.ring(d, a, b, r=46, color=CUR_COL, width=4)
        S.text(d, (a - 120, b + 52), "172 = current (continues NS1b)", size=17, bold=True, fill=CUR_COL, plate=S.WHITE)
    for r, yy_, pp_ in SP.NS1A_RANK_GAZES:
        if any(dd.charts[str(k)]["initialization_rank"] == r for k in dd.ids):
            a, b = NV.pano_xy(yy_, pp_, pw, ph)
            S.crosshair(d, a, b, r=10, color=S.INK)
            S.text(d, (a + 14, b + 10), f"chart centre (rank {r})", size=14, fill=S.INK, plate=S.WHITE)
    img.paste(pano, (40, y))
    d = ImageDraw.Draw(img)
    d.rectangle([40, y, 40 + pw, y + ph], outline=S.INK2, width=2)
    S.badge(img, 40 + pw - 8, y + 8, DER)
    xs = 40 + pw + 24
    S.text(d, (xs, y + 4), "COHERENT_SEED_SET", size=S.T_BODY, bold=True)
    S.text(d, (xs, y + 34), "initialized AND 1 contributing patch", size=15, fill=S.INK2)
    yy = y + 64
    for k in dd.ids:
        rec = rec0[str(k)]
        d.rectangle([xs, yy + 5, xs + 14, yy + 19], fill=dd.color[k])
        S.text(d, (xs + 22, yy), f"{k:>4}  rank {rec['initialization_rank']}  {rec['map']['surfels']:>6,} surfels",
               size=16, bold=k == SP.CONTINUING)
        yy += 25
    yy += 14
    S.text(d, (xs, yy), SP.LABEL_DEFERRED, size=15, bold=True, fill=S.INK2)
    yy += 24
    for r_ in dd.s0["deferred"]:
        S.xmark(d, xs + 7, yy + 11, r=5, color=DEF_COL, width=2)
        S.text(d, (xs + 22, yy), f"{r_['temporary_entity_id']:>4}  {r_['contributing_patches']} patches - NOT in the "
                                 f"scheduler", size=15, fill=S.INK2)
        yy += 23
    yy += 14
    for ln in ["Backdrop: coarse 360 RGB (RGB only).", "Dots: canonical-H0 persistent maps", "at the NS1c start.",
               "Cross-hairs: chart centres", "(NS1a initialization gazes).", "", "PHYSICAL HEAD FIXED;",
               "charts are policy geometry only."]:
        S.text(d, (xs, yy), ln, size=15, fill=S.INK2)
        yy += 22
    return y + ph + 20


def panel_b(img: Image.Image, y: int, dd: Data) -> int:
    y = NV.panel_title(img, y, "B", "Initial service map: every coherent entity probed ONCE before any render",
                       [SP.LABEL_CHART, "accepted FSG6f -> Cyclopean + gate v1"])
    d = ImageDraw.Draw(img)
    rows = {int(r["temporary_entity_id"]): r for r in dd.table["rows"]}
    cw, chh = 452, 280
    for i, k in enumerate(dd.ids):
        r = rows[k]
        x0, y0 = 40 + (i % 5) * (cw + 14), y + (i // 5) * chh
        tile(img, (x0, y0, x0 + cw, y0 + 70), r["service_state"], f"entity {k}")
        d = ImageDraw.Draw(img)
        if k == SP.CONTINUING:
            d.rectangle([x0 - 4, y0 - 4, x0 + cw + 4, y0 + 74], outline=CUR_COL, width=3)
        ch = dd.charts[str(k)]
        lines = [f"rank {r['initialization_rank']} - {r['map_surfels']:,} surfels - {r['own_looks']} own look(s)",
                 f"chart centre H0 {fmt(ch['seed_gaze_H0_deg'], 2)}",
                 f"current local gaze {fmt(r['current_local_gaze'])}",
                 f"FSG6f {r['fsg6f']}" + (f"; Cyclopean {r['cyclopean']}" if r["cyclopean"] else ""),
                 f"proposal {r['proposal_source'] or 'none'} local {fmt(r['proposed_local_gaze'])}",
                 f"gate: {r['gate_reason']}",
                 f"novel serviceable support {r['novel_serviceable_support'] if r['novel_serviceable_support'] is not None else '-'}"]
        text_block(d, x0 + 4, y0 + 78, lines, size=15, gap=24)
    yd = y + 2 * chh + 6
    S.text(d, (40, yd), f"{SP.LABEL_DEFERRED}: multi-part oracle ids, excluded by the single-patch rule; never in "
                        "the scheduler (not QUIET / UNLOCATED / BLOCKED)", size=16, bold=True, fill=S.INK2)
    for i, r_ in enumerate(dd.s0["deferred"]):
        x0 = 40 + i * 470
        tile(img, (x0, yd + 30, x0 + 450, yd + 96), "DEFERRED", f"entity {r_['temporary_entity_id']} - "
                                                                 f"{r_['contributing_patches']} patches")
    d = ImageDraw.Draw(img)
    rep = dd.table.get("ns1b_reproduction") or {}
    S.text(d, (1460, yd + 34), f"172 reproduces the accepted NS1b post-action probe: "
                               f"{'EXACT' if rep.get('reproduced') else 'NO'} ({rep.get('difference_count', '-')} diffs)",
           size=16, bold=True, fill=CUR_COL)
    S.text(d, (1460, yd + 62), "baseline-rotation invariance per entity: "
                               + ("all pass" if all(all(r["rotation_invariance"]) for r in rows.values()) else "FAIL"),
           size=16)
    return yd + 116


def action_rows(dd: Data) -> list[dict]:
    out = []
    for s in dd.steps:
        a, f = s["dec"]["action"], s["fus"]
        out.append({"k": s["k"], "target": int(a["target"]), "reason": s["dec"]["scheduler_reason"],
                    "local": a["local_gaze_deg"], "world": a["world_gaze_deg"], "before": f["map_before"],
                    "after": f["map_after"], "fusion": f["action"], "points": f["measured_points"],
                    "service_after": s["upd"]["service_after"]["label"]})
    return out


def panel_c(img: Image.Image, y: int, dd: Data) -> int:
    y = NV.panel_title(img, y, "C", "Attention timeline: every NS1c physical action, in order",
                       [SP.LABEL_SCHEDULER, SP.LABEL_CHART, SP.LABEL_H0])
    d = ImageDraw.Draw(img)
    acts = action_rows(dd)
    n = max(1, len(acts))
    cw = int(min(300, (W - 80 - 230) / n - 26))
    x = 40
    card_h = 268
    d.rectangle([x, y + 20, x + 200, y + 20 + card_h], fill=S.PANEL, outline=S.INK2, width=2)
    text_block(d, x + 10, y + 30, [("start", S.INK), "current 172", "(NS1b continuation)", "2 own looks",
                                   "21,243 surfels", "bout 1"], size=16, gap=26)
    prev_x = x + 200
    prev_t = SP.CONTINUING
    for a in acts:
        x = prev_x + 26
        first_switch = dd.switch is not None and a["k"] == dd.switch["k"]
        col = dd.color.get(a["target"], S.INK)
        mid = y + 20 + card_h / 2
        S.arrow(d, prev_x + 2, mid, x - 2, mid, color=CUR_COL if first_switch else S.INK2,
                width=4 if first_switch else 3, head=12, double=a["target"] != prev_t)
        d.rectangle([x, y + 20, x + cw, y + 20 + card_h], fill=S.PANEL, outline=col, width=5 if first_switch else 2)
        lines = [(f"step {a['k']}", S.INK), (f"target {a['target']}", col), f"{a['reason']}",
                 f"local {fmt(a['local'])}", f"H0 {fmt(a['world'], 2)}",
                 f"map {a['before']:,} -> {a['after']:,}", f"{a['fusion']}", f"after: {a['service_after']}"]
        text_block(d, x + 8, y + 28, lines, size=14 if cw < 240 else 16, gap=29)
        if first_switch:
            S.text(d, (x, y - 6), "FIRST TARGET SWITCH", size=17, bold=True, fill=CUR_COL, plate=S.WHITE)
        prev_x, prev_t = x + cw, a["target"]
    end = dd.final["stop"]["event"] if dd.final else (dd.terminal["outcome_reading"] if dd.terminal else "in progress")
    S.text(d, (40, y + card_h + 34), f"end: {end}", size=17, bold=True)
    S.text(d, (40, y + card_h + 62), "single arrow: retain (same target); double arrow: switch (accepted "
                                     "integrated.schedule); bold vermillion: the first spread of attention", size=15,
           fill=S.INK2)
    return y + card_h + 96


def panel_d(img: Image.Image, y: int, dd: Data) -> int:
    y = NV.panel_title(img, y, "D", "First cross-entity action" if dd.switch else "No cross-entity action",
                       [SP.LABEL_ORACLE_CORR, SP.LABEL_GEOMETRY, SP.LABEL_SEGMENTATION, SP.LABEL_H0])
    d = ImageDraw.Draw(img)
    if dd.switch is None:
        S.text(d, (50, y + 10), f"No action on a target other than 172 occurred: {dd.outcome()}", size=S.T_BODY,
               bold=True)
        return y + 60
    s = dd.switch
    dec, fu, upd = s["dec"], s["fus"], s["upd"]
    t = int(dec["action"]["target"])
    prev_state = dd.states[dd.steps.index(s)]
    rec_before = prev_state["entities"][str(t)]
    lines = [(f"172 -> {t}", NEW_COL),
             f"scheduler: {dec['scheduler_reason']} (accepted integrated.schedule)",
             f"172 was {prev_state['entities'][str(SP.CONTINUING)]['service']['label']}; next serviceable id above "
             f"172 (wrapping) = {t}",
             f"summaries seen: " + ", ".join(f"{a}:{b}" for a, b in dec["scheduler_decision"]["summaries"][:5]),
             "   " + ", ".join(f"{a}:{b}" for a, b in dec["scheduler_decision"]["summaries"][5:]),
             f"{t}: rank {rec_before['initialization_rank']} seed, {rec_before['map']['surfels']:,} surfels, "
             f"{rec_before['own_looks']} own look",
             f"proposal {dec['action']['source']} local {fmt(dec['action']['local_gaze_deg'])}",
             f"-> H0 {fmt(dec['action']['world_gaze_deg'], 3)}",
             f"PERFECT correspondences {s['osum']['correspondences']:,}",
             f"target points {fu['measured_points']:,}; fusion {fu['action']}",
             f"map {fu['map_before']:,} -> {fu['map_after']:,} (matched {fu['matched']:,}, new {fu['new']:,})"]
    text_block(d, 50, y + 6, lines, size=16, gap=27)
    # seed map of the new entity around its chart centre, with the executed fixation
    ch = dd.charts[str(t)]
    w1, h1 = 520, 420
    im, dd_ = new_panel(w1, h1, f"{t}: map + fixation", SP.LABEL_H0)
    sy, sp_ = ch["seed_gaze_H0_deg"]
    inner = (16, 48, w1 - 16, h1 - 16)
    yr, pr = (sy - 22, sy + 22), (sp_ - 18, sp_ + 18)

    def h0xy(yaw, pitch):
        yaw = (np.asarray(yaw, float) - sy + 180.0) % 360.0 - 180.0 + sy
        return eq_xy(yaw, pitch, inner, yr, pr)
    xyz = dd.map_of(rec_before)
    a, b = h0xy(*angles(xyz[sub(len(xyz))]))
    dots(dd_, a, b, NEW_COL, r=1, box=inner)
    ca, cb = h0xy(sy, sp_)
    S.crosshair(dd_, float(ca), float(cb), r=10, color=S.INK2)
    fa, fb = h0xy(*dec["action"]["world_gaze_deg"])
    S.crosshair(dd_, float(fa), float(fb), r=14, color=NEW_COL)
    lx = float(fa) + 18 if float(fa) < w1 - 160 else float(fa) - 150
    S.text(dd_, (lx, float(fb) - 30), "executed fixation", size=14, bold=True, fill=NEW_COL)
    img.paste(im, (860, y))
    # the new observation and its correspondences
    rgb = npz(s["sd"] / f"{SP.OBS_ACQ}/rgb-observation.npz")["rgb_L"]
    size = 360
    img.paste(NV.core_rgb_tile(rgb, size), (1400, y + 40))
    d = ImageDraw.Draw(img)
    S.text(d, (1400, y + 8), f"new observation (step {s['k']}, 4096 spp)", size=15, bold=True)
    cls = npz(s["sd"] / "correspondence/core-class-map.npz")["core_class"]
    prod = npz(s["sd"] / "correspondence/oracle-correspondences.npz")
    ids = npz(s["sd"] / "segmentation/local-identity.npz")["temporary_entity_id"]
    t_ = np.full((256, 256, 3), NV.NO_HIT_BG, np.uint8)
    t_[cls == 1] = NV.UNASSIGNED_BG
    t_[cls == 2] = NV.NOTVIS_BG
    rr, cc = prod["left_core_row"], prod["left_core_col"]
    t_[rr[ids > 0], cc[ids > 0]] = (170, 170, 170)
    t_[rr[ids == t], cc[ids == t]] = NEW_COL
    img.paste(Image.fromarray(t_).resize((size, size), Image.NEAREST), (1790, y + 40))
    NV.class_overlays(img, cls, 1790, y + 40, size)
    d = ImageDraw.Draw(img)
    S.text(d, (1790, y + 8), f"target {t} (blue) vs other ids (grey)", size=15, bold=True)
    S.text(d, (1400, y + 410), "ORACLE CORRESPONDENCE -> DERIVED SPHERICAL GEOMETRY -> ORACLE SEGMENTATION AID; "
                               "only the target is fused", size=14, fill=S.INK2)
    return y + 440


def panel_e(img: Image.Image, y: int, dd: Data) -> int:
    y = NV.panel_title(img, y, "E", "Scene state after the stop (canonical H0)" if dd.final else "Scene state at the end",
                       [SP.LABEL_H0, SP.LABEL_NOT_EXECUTED])
    last = dd.last
    w1, h1 = 900, 640
    im, d = new_panel(w1, h1, "all coherent maps, top view (X right, -Z up; metres)", SP.LABEL_H0)
    allp = [dd.map_of(last["entities"][str(k)]) for k in dd.ids]
    pts = np.vstack([p[sub(len(p), 3000)] for p in allp] + [np.zeros((1, 3))])
    umin, umax = pts[:, 0].min(), pts[:, 0].max()
    vmin, vmax = (-pts[:, 2]).min(), (-pts[:, 2]).max()
    s = min((w1 - 80) / max(1e-6, umax - umin), (h1 - 120) / max(1e-6, vmax - vmin))
    ox = (w1 - s * (umax - umin)) / 2 - s * umin
    oy = h1 - 30 - ((h1 - 90) - s * (vmax - vmin)) / 2 + s * vmin
    for k, p in zip(dd.ids, allp):
        q = p[sub(len(p), 3000)]
        dots(d, ox + s * q[:, 0], oy - s * (-q[:, 2]), dd.color[k], r=1, box=(2, 40, w1 - 2, h1 - 2))
        c = np.median(p, axis=0)
        S.text(d, (ox + s * c[0] + 6, oy + s * c[2] - 10), str(k), size=14, bold=True, fill=dd.color[k])
    hx, hy = ox, oy
    d.line([hx - 6, hy, hx + 6, hy], fill=S.INK, width=5)
    S.text(d, (hx + 8, hy + 4), "fixed head (H0 origin)", size=13, fill=S.INK)
    BV.scale_bar(d, 20, h1 - 30, s, metres=0.5)
    img.paste(im, (40, y))
    d = ImageDraw.Draw(img)
    x = 970
    S.text(d, (x, y), "service-state table (frozen)" if dd.final else "service-state table", size=S.T_BODY, bold=True)
    yy = y + 34
    cols = [(30, "id"), (90, "state"), (290, "looks"), (360, "surfels"), (470, "proposal (local)"), (650, "gate"),
            (1010, "probe")]
    for cx, lab in cols:
        S.text(d, (x + cx, yy), lab, size=15, bold=True)
    yy += 26
    for r in last["table"]:
        k = int(r["temporary_entity_id"])
        tile(img, (x, yy, x + 22, yy + 20), r["service_state"], "")
        d = ImageDraw.Draw(img)
        p = r["proposal"]
        hi = k == SP.CONTINUING or (dd.switch is not None and k == int(dd.switch["dec"]["action"]["target"]))
        vals = [str(k), r["service_state"], str(r["own_looks"]), f"{r['map_surfels']:,}",
                fmt(p["local_gaze_deg"]) if p else "none", r["gate"]["reason"], r["probe_provenance"]]
        for (cx, _lab), v in zip(cols, vals):
            S.text(d, (x + cx, yy), v, size=14, bold=hi, fill=dd.color[k] if hi else S.INK)
        yy += 26
    yy += 10
    if dd.final:
        st = dd.final["stop"]
        p = st["post_action_probe_of_new_target"]
        S.crosshair(d, x + 16, yy + 18, r=12, solid=False, color=NEW_COL)
        pr = p["proposal"]
        S.text(d, (x + 40, yy), f"next proposal of {st['to']}: " + (
            f"{pr['source']} local {fmt(pr['local_gaze_deg'])} -> H0 {fmt(pr['world_gaze_deg'], 2)}" if pr else "none")
               + f"  [{p['state']}]", size=16, bold=True, fill=NEW_COL)
        S.text(d, (x + 40, yy + 28), f"{SP.LABEL_NOT_EXECUTED}: NS1c stops after the first cross-entity action",
               size=16, bold=True)
        yy += 60
    S.text(d, (x, yy), f"accumulated physical observations: {last['executed_actions']}; probe calls "
                       f"{last['probe_calls']}, cache hits {last['probe_cache_hits']}", size=15, fill=S.INK2)
    S.text(d, (x, yy + 26), f"deferred (not in the scheduler): {dd.deferred}", size=15, fill=S.INK2)
    S.text(d, (x, yy + 52), "the full Classroom is not closed (no scene-level closure claim)", size=15, fill=S.INK2)
    return y + h1 + 24


def overview(dd: Data) -> tuple[Image.Image, dict]:
    img = Image.new("RGB", (W, 4200), S.SURFACE)
    y = NV.header(img, "North Star-1c - coherent multi-entity control: the first scene switch", [
        "From the accepted NS1b state, the accepted scheduler (integrated.schedule) and per-entity recentered local "
        "controllers service 172, then switch to another coherent RGB-bootstrap seed.",
        "PHYSICAL HEAD FIXED - POLICY CHART ONLY: every projection, calibration and observation stays in canonical H0; "
        "persistent fusion happens in H0, target only.",
        f"Reading: {dd.outcome()}"], BADGES["overview.png"])
    y = panel_a(img, y + 6, dd)
    y = panel_b(img, y, dd)
    y = panel_c(img, y, dd)
    y = panel_d(img, y, dd)
    y = panel_e(img, y, dd)
    img = img.crop((0, 0, W, y + 20))
    return img, {"panels": ["A", "B", "C", "D", "E"], "switch_step": None if dd.switch is None else dd.switch["k"],
                 "deferred_shown": dd.deferred,
                 "scheduler_reasons_shown": [s["dec"]["scheduler_reason"] for s in dd.steps]}


# ------------------------------------------------------------------ the scheduler timeline
def timeline(dd: Data) -> tuple[Image.Image, dict]:
    ncol = len(dd.states)
    cw = int(min(170, (W - 300) / max(1, ncol)))
    extra = [k for k in dd.deferred if k not in dd.ids]
    rows = dd.ids + extra
    rh = 54
    H = 260 + rh * len(rows) + 200
    img = Image.new("RGB", (W, H), S.SURFACE)
    y = NV.header(img, "North Star-1c - scene scheduler timeline", [
        "Rows: entities (coherent seeds; deferred identities greyed, never in the scheduler). Columns: the initial probe "
        "and the state after each global action.",
        "Bold frame: the current target; double arrow: switch; single arrow: retain (accepted integrated.schedule)."],
                  BADGES["scene-scheduler-timeline.png"])
    d = ImageDraw.Draw(img)
    x0, y0 = 240, y + 50
    for ci, st in enumerate(dd.states):
        lab = "initial" if st["global_step"] < 0 else f"after step {st['global_step']}"
        S.text(d, (x0 + ci * cw + 6, y0 - 34), lab, size=15, bold=True)
    for ri, k in enumerate(rows):
        yy = y0 + ri * rh
        S.text(d, (40, yy + 12), f"{k}" + ("  (deferred)" if k in extra else ""), size=17,
               bold=k == SP.CONTINUING, fill=S.INK2 if k in extra else dd.color.get(k, S.INK))
        for ci, st in enumerate(dd.states):
            bx = (x0 + ci * cw + 4, yy + 4, x0 + (ci + 1) * cw - 8, yy + rh - 8)
            if k in extra:
                tile(img, bx, "DEFERRED", "")
                continue
            lab = st["entities"][str(k)]["service"]["label"]
            tile(img, bx, lab, {"ACTIONABLE": "ACT", "QUIET": "QUIET"}.get(lab, "BLOCKED") if cw >= 110 else "")
            d = ImageDraw.Draw(img)
            if int(st["current"]) == k:
                d.rectangle([bx[0] - 3, bx[1] - 3, bx[2] + 3, bx[3] + 3], outline=S.INK, width=4)
    d = ImageDraw.Draw(img)
    for ci, s in enumerate(dd.steps, start=1):
        prev_t = int(dd.states[ci - 1]["current"])
        t = int(s["dec"]["action"]["target"])
        ya = y0 + rows.index(prev_t) * rh + rh / 2
        yb = y0 + rows.index(t) * rh + rh / 2
        xa, xb = x0 + (ci - 1) * cw + cw - 10, x0 + ci * cw + 6
        sw = t != prev_t
        S.arrow(d, xa, ya, xb, yb, color=CUR_COL if sw else S.INK2, width=3, head=10, double=sw)
    yy = y0 + len(rows) * rh + 20
    for ci, s in enumerate(dd.steps, start=1):
        S.text(d, (x0 + ci * cw + 6, yy), f"{s['dec']['scheduler_reason']}", size=14, bold=True)
        S.text(d, (x0 + ci * cw + 6, yy + 22), f"-> {s['dec']['action']['target']}", size=14)
    end = "STOP: first spread of attention" if dd.final else (dd.terminal["outcome_reading"] if dd.terminal else "")
    S.text(d, (40, yy + 60), end, size=17, bold=True, fill=CUR_COL if dd.final else S.INK)
    img = img.crop((0, 0, W, yy + 100))
    return img, {"columns": ncol, "rows": rows, "deferred_shown": extra,
                 "scheduler_reasons_shown": [s["dec"]["scheduler_reason"] for s in dd.steps]}


# ------------------------------------------------------------------ growth 3-D
def entity_steps(dd: Data, k: int) -> list[dict]:
    return [s for s in dd.steps if int(s["dec"]["action"]["target"]) == k]


def growth_panels(img: Image.Image, y: int, dd: Data, k: int) -> int:
    rec0 = dd.s0["entities"][str(k)]
    m0 = dd.map_of(rec0)
    steps = entity_steps(dd, k)
    final = dd.map_of(dd.last["entities"][str(k)])
    n_prev = [len(m0)]
    for s in steps:
        n_prev.append(int(s["fus"]["map_after"]))
    d = ImageDraw.Draw(img)
    S.text(d, (40, y), f"entity {k}: {len(m0):,} surfels at the NS1c start -> {len(final):,} after "
                       f"{len(steps)} NS1c action(s)", size=S.T_BODY, bold=True, fill=dd.color[k])
    y += 34
    ch = dd.charts[str(k)]
    r = np.asarray(ch["R_HC"], float)
    g0 = np.asarray(ch["g0_H0"], float)
    views = (("top (X right, -Z up)", lambda p: (p[:, 0], -p[:, 2]), True),
             ("view along the chart centre (x_C / y_C)", lambda p: ((p @ r)[:, 0], (p @ r)[:, 1]), False))
    bw, bh = 1140, 640
    for i, (title, f, head) in enumerate(views):
        im, dp = new_panel(bw, bh, title, SP.LABEL_H0)
        allp = np.vstack([final] + ([np.zeros((1, 3))] if head else []))
        u, v = f(allp)
        umin, umax, vmin, vmax = u.min(), u.max(), v.min(), v.max()
        s = min((bw - 80) / max(1e-6, umax - umin), (bh - 120) / max(1e-6, vmax - vmin))
        ox = (bw - s * (umax - umin)) / 2 - s * umin
        oy = bh - 30 - ((bh - 90) - s * (vmax - vmin)) / 2 + s * vmin

        def xy(p, f=f, s=s, ox=ox, oy=oy):
            a, b = f(np.asarray(p, float).reshape(-1, 3))
            return ox + s * a, oy - s * b
        idx = np.arange(len(final))
        segs = [(idx < n_prev[0], SEED_COL, "at the NS1c start")]
        for si, s_ in enumerate(steps):
            segs.append(((idx >= n_prev[si]) & (idx < n_prev[si + 1]), STEP_COLS[si % len(STEP_COLS)],
                         f"new at step {s_['k']}"))
        for mask, col, _lab in segs:
            q = final[mask]
            a, b = xy(q[sub(len(q), 5000)])
            dots(dp, a, b, col, r=1, box=(2, 40, bw - 2, bh - 2))
        if head:
            hx, hy = xy(np.zeros((1, 3)))
            dp.line([float(hx[0]) - 6, float(hy[0]), float(hx[0]) + 6, float(hy[0])], fill=S.INK, width=5)
            S.text(dp, (float(hx[0]) + 8, float(hy[0]) + 4), "fixed head", size=13)
            ga, gb = xy(g0[None] * float(np.median(np.linalg.norm(final, axis=1))))
            S.dashed_line(dp, [(float(hx[0]), float(hy[0])), (float(ga[0]), float(gb[0]))], S.INK2, width=2)
        BV.scale_bar(dp, 20, bh - 30, s, metres=0.1 if not head else 0.5)
        yl = 50
        for mask, col, lab in segs:
            dp.rectangle([bw - 300, yl + 4, bw - 288, yl + 16], fill=col)
            S.text(dp, (bw - 280, yl), f"{lab} ({int(mask.sum()):,})", size=14)
            yl += 22
        img.paste(im, (40 + i * (bw + 40), y))
    y += bh + 16
    d = ImageDraw.Draw(img)
    for s_ in steps:
        fu = s_["fus"]
        md = fu.get("matched_distance_m") or {}
        med = f"{md['median'] * 1000:.2f} mm" if md else "-"
        S.text(d, (40, y), f"step {s_['k']}: local {fmt(fu['local_gaze_deg'])} -> H0 {fmt(fu['world_gaze_deg'], 2)}; "
                           f"target points {fu['measured_points']:,}; {fu['action']}; matched {fu['matched']:,} "
                           f"(median {med}); new {fu['new']:,}; {fu['map_before']:,} -> {fu['map_after']:,}", size=15)
        y += 24
    return y + 20


def growth_3d(dd: Data) -> tuple[Image.Image, dict]:
    img = Image.new("RGB", (W, 3200), S.SURFACE)
    y = NV.header(img, "North Star-1c - multi-entity growth in canonical H0", [
        "Persistent maps in canonical H0 (fixed head at the origin, baseline on +X); the NS1c-start map and the surfels "
        "each NS1c action added (target-only 12-mm fusion).", "PHYSICAL HEAD FIXED - POLICY CHART ONLY."],
                  BADGES["multi-entity-growth-3d.png"])
    shown = [SP.CONTINUING]
    if dd.switch is not None:
        shown.append(int(dd.switch["dec"]["action"]["target"]))
    for k in shown:
        y = growth_panels(img, y + 10, dd, k)
    if dd.switch is None:
        S.text(ImageDraw.Draw(img), (40, y), "no second entity was attended", size=S.T_BODY, bold=True)
        y += 40
    img = img.crop((0, 0, W, y + 10))
    return img, {"entities": shown}


# ------------------------------------------------------------------ controller vs North-Star support
def support(dd: Data) -> tuple[Image.Image, dict]:
    diag = dd.ctx["diagnostics"]
    bars = []
    for k in dd.ids:
        dg = diag[str(k)]
        bars.append({"label": f"{k} init look", "ctrl": dg["controller_state_target_support"],
                     "ns": dg["ns1a_initialization_look_target_points"], "kind": "init"})
    nb = diag[str(SP.CONTINUING)].get("ns1b_action_look")
    if nb:
        bars.append({"label": "172 NS1b action", "ctrl": nb["controller_state_target_support"],
                     "ns": nb["north_star_target_points"], "kind": "ns1b"})
    for s in dd.steps:
        bars.append({"label": f"step {s['k']} ({s['dec']['action']['target']})",
                     "ctrl": s["upd"]["controller_state_target_support"], "ns": s["upd"]["north_star_target_points"],
                     "kind": "action"})
    H = 1250
    img = Image.new("RGB", (W, H), S.SURFACE)
    y = NV.header(img, "North Star-1c - controller-state support vs North-Star measurement (descriptive)", [
        "Per look: the accepted Classroom matcher's valid target support (controller observation state, planar rectified "
        "core) vs the North-Star raw-core PERFECT spherical target points.",
        "Descriptive diagnostic only: it does not change the experiment or the controller."],
                  BADGES["controller-vs-northstar-support.png"])
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = 120, y + 40, W - 60, H - 170
    vmax = max(1, max(max(b["ctrl"], b["ns"]) for b in bars))
    d.line([x0, y1, x1, y1], fill=S.INK, width=2)
    d.line([x0, y0, x0, y1], fill=S.INK, width=2)
    for t in np.linspace(0, vmax, 6):
        yy = y1 - (y1 - y0) * t / vmax
        d.line([x0 - 6, yy, x1, yy], fill=S.GRID, width=1)
        S.text(d, (x0 - 100, yy - 10), f"{int(t):,}", size=14, fill=S.INK2)
    n = len(bars)
    gw = (x1 - x0 - 20) / max(1, n)
    bw = max(6.0, gw * 0.36)
    for i, b in enumerate(bars):
        gx = x0 + 10 + i * gw
        for j_, (v, col, hatch) in enumerate(((b["ctrl"], S.OI_ORANGE, True), (b["ns"], S.OI_BLUE, False))):
            bx = [gx + j_ * (bw + 4), y1 - (y1 - y0) * v / vmax, gx + j_ * (bw + 4) + bw, y1]
            d.rectangle(bx, fill=col)
            if hatch and bx[3] - bx[1] > 6:
                S.hatch(img, [int(c) for c in bx], S.WHITE, spacing=8, width=2)
                d = ImageDraw.Draw(img)
        S.text(d, (gx, y1 + 8), b["label"], size=13, fill=S.INK2 if b["kind"] != "action" else S.INK,
               bold=b["kind"] == "action")
        S.text(d, (gx, y1 + 28), f"{b['ctrl']:,} / {b['ns']:,}", size=12, fill=S.INK2)
    d.rectangle([x0, H - 110, x0 + 20, H - 92], fill=S.OI_ORANGE)
    S.hatch(img, [x0, H - 110, x0 + 20, H - 92], S.WHITE, spacing=8, width=2)
    d = ImageDraw.Draw(img)
    S.text(d, (x0 + 30, H - 112), "controller-state target support (matcher-valid target points)", size=15)
    d.rectangle([x0 + 700, H - 110, x0 + 720, H - 92], fill=S.OI_BLUE)
    S.text(d, (x0 + 730, H - 112), "North-Star raw-core target metric points (PERFECT, spherical)", size=15)
    return img, {"bars": len(bars), "actions": len(dd.steps)}


FIGURE_FUNCS = {"overview.png": overview, "scene-scheduler-timeline.png": timeline,
                "multi-entity-growth-3d.png": growth_3d, "controller-vs-northstar-support.png": support}


def render_all(run: Path) -> tuple[dict, Data]:
    dd = Data(Path(run))
    return {n: fn(dd) for n, fn in FIGURE_FUNCS.items()}, dd


def visualize(run: Path, vis: Path) -> dict:
    vis = Path(vis)
    vis.mkdir(parents=True, exist_ok=True)
    figs, dd = render_all(run)
    man = {"schema": "NS1c-visuals-v1", "visual_language": "Visual Language 1", "run": str(run),
           "font_hashes": S.font_hashes(), "figures": {}, "frames": {"chart": SP.LABEL_CHART, "h0": SP.LABEL_H0},
           "fixed_head_statement": SP.LABEL_FIXED_HEAD, "backdrop": {"path": str(SP.NB1A_RGB[0]),
                                                                    "sha256": SP.NB1A_RGB[1]},
           "outcome_reading": dd.outcome()}
    for name, (im, meta) in figs.items():
        path = vis / name
        im.save(path, format="PNG", optimize=False)
        man["figures"][name] = {"sha256": sha256(path), "size": list(im.size), "badges": BADGES[name],
                                "labels": LABELS[name], **meta}
    (vis / "visuals-manifest.json").write_text(json.dumps(man, indent=1, sort_keys=True) + "\n")
    return man
