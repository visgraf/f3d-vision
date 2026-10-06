"""North Star-1c2: the scientific visuals (Visual Language 1; deterministic PNGs).

Contract: docs/north-star/ns1c2-controller02-phase-semantics-contract.md, section 26.

- ``overview.png``: A the historical known answer (ACCEPTED HISTORICAL REFERENCE: the adapter's re-drive of the accepted
  Controller-02 history); B the semantic bug, side by side at the divergence state (NS1c vs NS1c2); C the corrected 172
  continuation (the replayed NS1c prefix, then the new actions); D the first valid scene switch; E the phase state (gate
  markers only inside RESIDUE).
- ``ns1c-vs-ns1c2-divergence.png``: the exact post-step-3 state and the two semantic outcomes, in canonical H0.
- ``controller-phase-timeline.png``: rows entities, columns states; NORMAL ACTIONABLE / NORMAL QUIET / DEFERRED /
  FINALIZED; current target; retain / switch; action source.
- ``multi-entity-growth-3d.png``: canonical-H0 growth of 172 and of the second entity.
- ``controller-vs-northstar-support.png``: descriptive; controller-state target support vs North-Star target points.

Only the NS1c2 run, NS1c's pinned records (comparison), the frozen NS1a maps (display only) and the RGB-only coarse 360
backdrop are read; no catalog and no name.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
for _p in (HERE, HERE.parent, HERE.parent / "active_bootstrap", HERE.parent / "visual_language", HERE.parents[1]):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import ns1a_visuals as NV  # noqa: E402  (accepted NS1a drawing helpers; its Data class is never used)
import ns1b_visuals as BV  # noqa: E402  (accepted NS1b drawing helpers; its Data class is never used)
import ns1c2_core as CORE  # noqa: E402
import ns1c2_spec as SP  # noqa: E402
import style as S  # noqa: E402  (Visual Language 1, read-only)

ORA, DER = SP.TRUTH_ORACLE, SP.TRUTH_DERIVED
W = NV.W
BADGES = {"overview.png": [ORA, DER], "ns1c-vs-ns1c2-divergence.png": [ORA, DER],
          "controller-phase-timeline.png": [DER], "multi-entity-growth-3d.png": [ORA, DER],
          "controller-vs-northstar-support.png": [ORA, DER]}
LABELS = {"overview.png": [SP.LABEL_HISTORICAL, SP.LABEL_NS1C_NOT_ACCEPTED, SP.LABEL_GATE_RESIDUE_ONLY,
                           SP.LABEL_NS1C_REPLAY, SP.LABEL_SCHEDULER, SP.LABEL_FIXED_HEAD, SP.LABEL_CHART, SP.LABEL_H0,
                           SP.LABEL_NOT_EXECUTED, SP.LABEL_ORACLE_CORR, SP.LABEL_GEOMETRY, SP.LABEL_SEGMENTATION,
                           SP.LABEL_NO_NAME],
          "ns1c-vs-ns1c2-divergence.png": [SP.LABEL_NS1C_NOT_ACCEPTED, SP.LABEL_GATE_RESIDUE_ONLY, SP.LABEL_H0,
                                           SP.LABEL_CHART, SP.LABEL_FIXED_HEAD],
          "controller-phase-timeline.png": [SP.LABEL_SCHEDULER, SP.LABEL_GATE_RESIDUE_ONLY, SP.LABEL_DEFERRED_ID,
                                            SP.LABEL_NS1C_REPLAY],
          "multi-entity-growth-3d.png": [SP.LABEL_H0, SP.LABEL_FIXED_HEAD, SP.LABEL_GEOMETRY, SP.LABEL_NS1C_REPLAY],
          "controller-vs-northstar-support.png": [SP.LABEL_ORACLE_CORR, SP.LABEL_GEOMETRY]}
CUR_COL, NEW_COL, SEED_COL, DEF_COL, NS1C_COL = S.OI_VERM, S.OI_BLUE, S.GEOM_FAR, (150, 150, 150), (150, 150, 150)
PALETTE = [S.OI_GREEN, S.OI_ORANGE, S.OI_PURPLE, S.OI_SKY, S.WINE, S.REF_BROWN, (90, 90, 90), (0, 90, 140),
           (160, 120, 0), (110, 60, 140)]
STEP_COLS = [S.OI_BLUE, S.OI_GREEN, S.OI_ORANGE, S.OI_PURPLE, S.OI_SKY, S.WINE, S.REF_BROWN, (0, 90, 140),
             (160, 120, 0), (110, 60, 140)]
SRC = {"fsg6f": ("FSG6f", S.OI_BLUE, "circle"), "cyclopean_epistemic": ("Cyclopean", S.OI_GREEN, "diamond"),
       "oracle_seed": ("seed", S.INK2, "square")}

j, npz, sub, dots, angles, eq_xy, text_block, new_panel = (BV.j, BV.npz, BV.sub, BV.dots, BV.angles, BV.eq_xy,
                                                           BV.text_block, BV.new_panel)


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fmt(v, nd=1) -> str:
    return "-" if v is None else f"({v[0]:+.{nd}f}, {v[1]:+.{nd}f})"


class Data:
    def __init__(self, run: Path) -> None:
        self.run = Path(run)
        self.charts = j(run / "charts/policy-charts.json")["charts"]
        self.ctx = j(run / "contexts/contexts.json")
        self.table = j(run / "initial-probe/initial-service-table.json")
        self.ka = j(run / "known-answer/known-answer.json")
        self.s0 = j(run / SP.scene_state_rel("initial"))
        afters = sorted((run / "scene").glob("state-after-step-*.json"))
        self.states = [self.s0] + [j(p) for p in afters]
        self.steps = []
        for st in self.states[1:]:
            k = int(st["global_step"])
            sd = run / SP.step_dir(k)
            obs = CORE.resolve(st["last_action"]["observation_source"], run)
            self.steps.append({"k": k, "dec": j(sd / "plan/decision.json"), "fus": j(sd / "fusion/fusion.json"),
                               "upd": j(sd / "update/update.json"), "after": st, "sd": sd, "obs": obs,
                               "prefix": SP.is_prefix(k), "osum": j(obs / "correspondence/oracle-summary.json")})
        self.div = j(run / "divergence/divergence.json") if (run / "divergence/divergence.json").exists() else None
        self.terminal = j(run / "scene/terminal.json") if (run / "scene/terminal.json").exists() else None
        self.final = j(run / "scene/final-scene-state.json") if (run / "scene/final-scene-state.json").exists() else None
        self.ids = [int(k) for k in self.s0["scene_ids"]]
        self.deferred = [int(r["temporary_entity_id"]) for r in self.s0["deferred"]]
        self.color = {k: (CUR_COL if k == SP.CONTINUING else PALETTE[i % len(PALETTE)]) for i, k in enumerate(self.ids)}
        self.switch = next((s for s in self.steps if int(s["dec"]["action"]["target"]) != SP.CONTINUING), None)
        if self.switch is not None:
            self.color[int(self.switch["dec"]["action"]["target"])] = NEW_COL
        self.pano = npz(SP.NB1A_RGB[0])["srgb8"]
        self.ns1a_maps = npz(SP.NS1A_RUN / SP.NS1A_MAPS)
        self.last = self.states[-1]
        self.ns1c_step4 = j(SP.NS1C_RUN / SP.NS1C_STEP4_DECISION)
        self.gate_events = [(st["global_step"], e) for st in self.states[1:] for e in st.get("events", [])
                            if e["event"] == "final_probe_decision"]

    def map_of(self, rec: dict) -> np.ndarray:
        return np.asarray(CORE.load_npz(CORE.resolve(rec["map"]["path"], self.run))["xyz_h"], float)

    def ns1a_map(self, k: int) -> np.ndarray:
        key = SP.map_key(k, "xyz_h")
        return np.asarray(self.ns1a_maps[key], float) if key in self.ns1a_maps else np.empty((0, 3))

    def phases(self) -> list[str]:
        return [st["phase"] for st in self.states]

    def outcome(self) -> str:
        if self.switch is not None:
            before = self.states[self.steps.index(self.switch)]["entities"][str(SP.CONTINUING)]["status"]["label"]
            if before == "QUIET":
                kind = "Outcome 1 - natural quiet switch (172 QUIET under NORMAL semantics)"
            elif "DEFERRED" in before:
                kind = "Outcome 2 - ordinary-budget switch (172 ACTIONABLE / DEFERRED:ordinary_budget)"
            else:
                kind = f"switch (172 {before})"
            if self.switch["fus"]["action"] != "FUSED":
                return f"{kind}; the second-entity action was retained, not fused (reading left to Luiz / Chat)"
            return kind
        if self.terminal is not None:
            return self.terminal.get("outcome_reading", "terminal")
        return "no cross-entity action"


def tile(img: Image.Image, box, label: str, text: str = "") -> None:
    """VL1 tiles: NORMAL ACTIONABLE / NORMAL QUIET; DEFERRED (hatched orange); FINALIZED actionable = RESIDUAL; the
    deferred ambiguous identities drawn apart (grey cross-hatch)."""
    if label in ("ACTIONABLE", "QUIET"):
        S.state_tile(img, box, label, text, size=S.T_SMALL)
    elif "DEFERRED" in label:
        S.state_tile(img, box, "DEFERRED", text, size=S.T_SMALL)
    elif "FINALIZED" in label:
        S.state_tile(img, box, "QUIET" if label.startswith("QUIET") else "RESIDUAL", text, size=S.T_SMALL)
    else:
        d = ImageDraw.Draw(img)
        d.rectangle(box, fill=(238, 238, 238))
        S.hatch(img, box, (190, 190, 190), spacing=9, width=2, cross=True)
        d = ImageDraw.Draw(img)
        S.dashed_rect(d, box, S.INK2, width=2)
        if text:
            S.text(d, (box[0] + 6, box[1] + 4), text, size=S.T_SMALL, bold=True)


def abbrev(label: str) -> str:
    """ACT / QUIET / ACT-DEF (DEFERRED) / FIN (FINALIZED) for compact status lists."""
    base = "ACT" if label.startswith("ACTIONABLE") else "QUIET" if label.startswith("QUIET") else label[:4]
    return base + ("-DEF" if "DEFERRED" in label else "-FIN" if "FINALIZED" in label else "")


def glyph(d, x, y, source, r=7):
    _name, col, kind = SRC.get(source, ("?", S.INK, "circle"))
    NV.glyph(d, x, y, kind, col, r=r)


def box(d, xy, lines, fill, outline, width=2, size=16, gap=24, dashed=False):
    x0, y0, x1, y1 = xy
    d.rectangle(xy, fill=fill)
    if dashed:
        S.dashed_rect(d, xy, outline, width=width)
    else:
        d.rectangle(xy, outline=outline, width=width)
    text_block(d, x0 + 10, y0 + 8, lines, size=size, gap=gap)


# ------------------------------------------------------------------ overview
def panel_a(img: Image.Image, y: int, dd: Data) -> int:
    y = NV.panel_title(img, y, "A", "Historical known answer: the local controller is already proven with an ideal "
                       "matcher", [SP.LABEL_HISTORICAL])
    d = ImageDraw.Draw(img)
    h = dd.ka["historical_controller02_trace"]
    lit = SP.HISTORICAL
    c1, c2_ = lit["controller01"], lit["controller02"]
    lines = [("Controller-01 (accepted; ideal / oracle matcher)", S.INK),
             f"{c1['localized_objects']} localized objects; {c1['observations']} observations; {c1['switches']} switches",
             f"{c1['natural_reactivations']} natural reactivations; {c1['final_active_map_surfels']:,} surfels",
             f"{c1['covered_samples_12mm']:,} / {c1['reachable_samples']:,} reachable samples within 12 mm "
             f"({100 * c1['micro_coverage']:.2f} %)",
             f"terminal: 24 QUIET, 1 watchdog-blocked ({c1['watchdog_blocked']})", "",
             ("Controller-02 (accepted)", S.INK),
             f"all {c2_['ordinary_actions_replayed']} ordinary actions replayed; only BLOCKED -> DEFERRED -> RESIDUE",
             f"gate only after NORMAL exhaustion: one call ({c2_['gate_object']}), rejected",
             "", ("values pinned from the accepted reports (not NS1c2 measurements)", S.INK2)]
    text_block(d, 50, y + 6, lines, size=16, gap=26)
    x0, x1, yy = 900, W - 60, y + 30
    S.text(d, (x0, y + 2), "NS1c2 phase adapter re-driving the accepted Controller-02 history (name-free records):",
           size=16, bold=True)
    seq = h.get("action_sequence", [])
    n = max(1, len(seq) + 1)
    sx = (x1 - x0) / n
    d.rectangle([x0, yy + 20, x1, yy + 90], fill=S.PANEL, outline=S.INK2, width=1)
    res_from = next((p["from_global_step"] for p in h["phases"] if p["phase"] == "RESIDUE"), None)
    if res_from is not None:
        rx = x0 + sx * res_from
        d.rectangle([rx, yy + 20, x1, yy + 90], fill=(253, 236, 214))
        S.text(d, (rx - 40, yy + 94), "RESIDUE", size=14, bold=True, fill=S.OI_VERM)
    for step, _t, src, _ph, reason in seq:
        x = x0 + sx * (step + 0.5)
        glyph(d, x, yy + 55, src, r=4)
        if reason in ("switch", "natural_reactivation"):
            d.line([x, yy + 24, x, yy + 34], fill=S.INK2, width=2)
    for dfe in h["deferred"]:
        x = x0 + sx * (dfe["global_step"] + 0.5)
        d.line([x, yy + 20, x, yy + 90], fill=S.OI_ORANGE, width=3)
        S.text(d, (x - 90, yy - 2), f"{dfe['object']} DEFERRED at {dfe['fixations']} looks", size=14, bold=True,
               fill=S.OI_ORANGE, plate=S.WHITE)
    for gc in h["gate_calls"]:
        x = x0 + sx * (gc["global_step"] + 0.5) - 6
        NV.glyph(d, x, yy + 55, "diamond", S.OI_VERM, r=9)
        S.text(d, (min(x - 210, x1 - 380), yy + 116), f"final-look gate: {gc['object']} ({gc['phase']}), rejected",
               size=14, bold=True, fill=S.OI_VERM)
    yl = yy + 150
    for src in ("oracle_seed", "fsg6f", "cyclopean_epistemic"):
        glyph(d, x0 + 10, yl + 9, src, r=6)
        S.text(d, (x0 + 24, yl), f"{SRC[src][0]} look ({h['sources'][src]})", size=14)
        x0 += 230
    x0 = 900
    ok = dd.ka["historical_controller02_trace"]["ok"]
    S.text(d, (x0, yl + 30), f"re-drive: {h['actions']} / 141 actions equal; {h['events']} / 56 events equal; "
                             f"{h['switches']} switches ({h['natural_reactivation_switches']} natural reactivation); "
                             f"gate calls in NORMAL {h['gate_calls_in_normal']} -> {'PASS' if ok else 'FAIL'}",
           size=15, bold=True)
    return y + 330


def flow(img, x, y, w, title, rows, accent, struck=False):
    d = ImageDraw.Draw(img)
    S.text(d, (x, y), title, size=S.T_BODY, bold=True, fill=accent)
    yy = y + 40
    for i, (text, kind) in enumerate(rows):
        fill = {"gate": (250, 232, 220), "gate_absent": (234, 246, 240), "state_bad": (236, 236, 236),
                "state_ok": S.WHITE, "sched_bad": (236, 236, 236), "sched_ok": S.WHITE}.get(kind, S.PANEL)
        outline = {"gate": S.OI_VERM, "gate_absent": S.OI_GREEN, "state_ok": S.OI_BLUE, "sched_ok": S.OI_BLUE}.get(
            kind, S.INK2)
        bx = (x, yy, x + w, yy + 54)
        d.rectangle(bx, fill=fill)
        if kind == "gate_absent":
            S.dashed_rect(d, bx, outline, width=3)
        else:
            d.rectangle(bx, outline=outline, width=4 if kind in ("gate", "state_ok", "sched_ok") else 2)
        S.text(d, (x + 12, yy + 14), text, size=16, bold=kind in ("gate", "gate_absent", "state_ok", "sched_ok"))
        if i < len(rows) - 1:
            S.arrow(d, x + w / 2, yy + 56, x + w / 2, yy + 74, color=S.INK2, width=3, head=10)
        yy += 76
    if struck:
        d.line([x - 6, y + 34, x + w + 6, yy - 18], fill=(170, 170, 170), width=3)
    return yy


def divergence_rows(dd: Data):
    c = dd.div["comparison"]
    a, b = c["NS1c"], c["NS1c2"]
    left = [(f"FSG6f: {a['fsg6f']}", "plain"),
            (f"Cyclopean proposal local {fmt(a['cyclopean_proposal_local'])}", "plain"),
            ("FINAL GATE v1 - wrongly applied in NORMAL", "gate"),
            (f"REJECT: {a['gate_verdict']['reason']}", "gate"),
            (f"service state: {a['service_state']}", "state_bad"),
            (f"scheduler: {a['scheduler']['reason'].upper()} -> {a['scheduler']['target']}", "sched_bad")]
    sch = b["scheduler"] or {}
    right = [(f"FSG6f: {b['fsg6f']}", "plain"),
             (f"Cyclopean proposal local {fmt(b['cyclopean_proposal_local'])}", "plain"),
             ("NO FINAL GATE IN NORMAL (gate: RESIDUE only)", "gate_absent"),
             (f"gate calls: {b['gate_calls']}", "gate_absent"),
             (f"NORMAL local state: {b['service_state']}", "state_ok"),
             (f"schedule_normal: {str(sch.get('reason', 'none')).upper()} -> {sch.get('target')}", "sched_ok")]
    return left, right


def panel_b(img: Image.Image, y: int, dd: Data) -> int:
    y = NV.panel_title(img, y, "B", "The semantic bug, at the exact post-step-3 state of 172 (the first true divergence)",
                       [SP.LABEL_NS1C_NOT_ACCEPTED, SP.LABEL_GATE_RESIDUE_ONLY])
    d = ImageDraw.Draw(img)
    if dd.div is None:
        S.text(d, (50, y + 10), "the divergence record does not exist (the prefix did not complete)", size=S.T_BODY,
               bold=True)
        return y + 60
    st = dd.div["state"]
    S.text(d, (50, y + 4), f"172: {st['own_looks']} own looks, {st['map_surfels']:,} surfels, revision {st['revision']}, "
                           f"chart {st['chart_id']}; the same probe input for both semantics", size=16, fill=S.INK2)
    left, right = divergence_rows(dd)
    yl = flow(img, 50, y + 40, 1050, "NS1c (NOT ACCEPTED): gate v1 applied to every ordinary probe", left, NS1C_COL,
              struck=False)
    yr = flow(img, 1250, y + 40, 1080, "NS1c2: accepted Controller-02 NORMAL semantics", right, S.OI_BLUE)
    d = ImageDraw.Draw(img)
    S.text(d, (50, max(yl, yr) + 4), "The 172 -> 123 switch of NS1c is mechanically real but is NOT accepted evidence of "
                                     "the Controller-02 scene-switch semantics.", size=16, bold=True, fill=S.INK2)
    return max(yl, yr) + 44


def action_rows(dd: Data) -> list[dict]:
    out = []
    for s in dd.steps:
        a, f = s["dec"]["action"], s["fus"]
        out.append({"k": s["k"], "target": int(a["target"]), "reason": s["dec"]["scheduler_reason"],
                    "source": a["source"], "phase": a["phase"], "local": a["local_gaze_deg"],
                    "world": a["world_gaze_deg"], "before": f["map_before"], "after": f["map_after"],
                    "fusion": f["action"], "points": f["measured_points"], "prefix": s["prefix"],
                    "status_after": s["upd"]["status_after"]["label"]})
    return out


def panel_c(img: Image.Image, y: int, dd: Data) -> int:
    y = NV.panel_title(img, y, "C", "Corrected 172 continuation", [SP.LABEL_NS1C_REPLAY, SP.LABEL_CHART, SP.LABEL_H0])
    d = ImageDraw.Draw(img)
    acts = [a for a in action_rows(dd) if a["target"] == SP.CONTINUING]
    per_row = 8
    cw, chh = 268, 262
    for i, a in enumerate(acts):
        x0 = 40 + (i % per_row) * (cw + 20)
        y0 = y + 10 + (i // per_row) * (chh + 24)
        fill = (241, 241, 241) if a["prefix"] else S.PANEL
        d.rectangle([x0, y0, x0 + cw, y0 + chh], fill=fill)
        if a["prefix"]:
            S.dashed_rect(d, (x0, y0, x0 + cw, y0 + chh), S.INK2, width=2)
        else:
            d.rectangle([x0, y0, x0 + cw, y0 + chh], outline=CUR_COL, width=3)
        glyph(d, x0 + cw - 18, y0 + 18, a["source"], r=9)
        lines = [(f"step {a['k']}" + ("  (NS1c, replayed)" if a["prefix"] else "  NEW"), S.INK),
                 f"{a['reason']} - {SRC[a['source']][0]}", f"local {fmt(a['local'])}", f"H0 {fmt(a['world'], 2)}",
                 f"map {a['before']:,}", f"  -> {a['after']:,}", f"{a['fusion']} ({a['points']:,} pts)",
                 f"after: {a['status_after']}"]
        text_block(d, x0 + 8, y0 + 8, lines, size=15, gap=29)
    rows = max(1, (len(acts) + per_row - 1) // per_row)
    yb = y + 10 + rows * (chh + 24)
    S.text(d, (40, yb), "dashed grey cards: NS1c's measured observations, replayed read-only after the corrected NORMAL "
                        "decisions selected them (no re-render); red cards: new NS1c2 observations (4096 spp).",
           size=15, fill=S.INK2)
    return yb + 36


def panel_d(img: Image.Image, y: int, dd: Data) -> int:
    y = NV.panel_title(img, y, "D", "First valid scene switch" if dd.switch else "No second-entity action",
                       [SP.LABEL_SCHEDULER, SP.LABEL_ORACLE_CORR, SP.LABEL_GEOMETRY, SP.LABEL_SEGMENTATION])
    d = ImageDraw.Draw(img)
    if dd.switch is None:
        S.text(d, (50, y + 10), f"No action on a target other than 172 occurred: {dd.outcome()}", size=S.T_BODY,
               bold=True)
        return y + 60
    s = dd.switch
    dec, fu = s["dec"], s["fus"]
    t = int(dec["action"]["target"])
    prev_state = dd.states[dd.steps.index(s)]
    rec_before = prev_state["entities"][str(t)]
    st172 = prev_state["entities"][str(SP.CONTINUING)]["status"]["label"]
    sd_ = dec["scheduler_decision"]
    lines = [(f"172 -> {t}", NEW_COL),
             f"172 before the switch: {st172}",
             f"schedule_normal: {sd_['result']['reason']} -> {sd_['result']['target_id']}",
             "statuses seen: " + ", ".join(f"{a}:{abbrev(b)}" for a, b in sd_["statuses"][:5]),
             "   " + ", ".join(f"{a}:{abbrev(b)}" for a, b in sd_["statuses"][5:]),
             f"{t}: rank {rec_before['initialization_rank']} seed, {rec_before['map']['surfels']:,} surfels, "
             f"{rec_before['own_looks']} own look(s)",
             f"proposal {SRC[dec['action']['source']][0]} local {fmt(dec['action']['local_gaze_deg'])}",
             f"-> H0 {fmt(dec['action']['world_gaze_deg'], 3)}",
             f"PERFECT correspondences {s['osum']['correspondences']:,}",
             f"target points {fu['measured_points']:,}; fusion {fu['action']}",
             f"map {fu['map_before']:,} -> {fu['map_after']:,} (matched {fu['matched']:,}, new {fu['new']:,})"]
    text_block(d, 50, y + 6, lines, size=16, gap=27)
    ch = dd.charts[str(t)]
    w1, h1 = 560, 420
    im, dp = new_panel(w1, h1, f"{t}: seed + new surfels", SP.LABEL_H0)
    fy, fp = dec["action"]["world_gaze_deg"]
    inner = (16, 48, w1 - 16, h1 - 16)
    seed = dd.map_of(rec_before)
    fused = dd.map_of(s["after"]["entities"][str(t)])
    new = fused[len(seed):] if len(fused) > len(seed) else np.empty((0, 3))
    ya, pa = angles(np.vstack([seed, new]) if len(new) else seed)
    span = max(4.0, float(np.ptp(((ya - fy + 180) % 360) - 180)) * 0.6, float(np.ptp(pa)) * 0.6)
    yr, pr = (fy - span, fy + span), (fp - span * 0.75, fp + span * 0.75)

    def h0xy(yaw, pitch):
        yaw = (np.asarray(yaw, float) - fy + 180.0) % 360.0 - 180.0 + fy
        return eq_xy(yaw, pitch, inner, yr, pr)
    a, b = h0xy(*angles(seed))
    dots(dp, a, b, SEED_COL, r=1, box=inner)
    if len(new):
        a, b = h0xy(*angles(new[sub(len(new))]))
        dots(dp, a, b, NEW_COL, r=1, box=inner)
    sy, sp_ = ch["seed_gaze_H0_deg"]
    ca, cb = h0xy(sy, sp_)
    S.ring(dp, float(ca), float(cb), r=7, color=S.INK2, width=2)
    fa, fb = h0xy(fy, fp)
    S.crosshair(dp, float(fa), float(fb), r=12, color=CUR_COL)
    S.text(dp, (18, h1 - 42), f"grey: seed map ({len(seed):,}); blue: new surfels ({len(new):,}); red: fixation",
           size=13)
    img.paste(im, (900, y))
    rgb = npz(s["obs"] / f"{SP.OBS_ACQ}/rgb-observation.npz")["rgb_L"]
    size = 330
    img.paste(NV.core_rgb_tile(rgb, size), (1500, y + 40))
    d = ImageDraw.Draw(img)
    S.text(d, (1500, y + 8), f"new observation (step {s['k']})", size=15, bold=True)
    cls = npz(s["obs"] / "correspondence/core-class-map.npz")["core_class"]
    prod = npz(s["obs"] / "correspondence/oracle-correspondences.npz")
    ids = npz(s["obs"] / "segmentation/local-identity.npz")["temporary_entity_id"]
    t_ = np.full((256, 256, 3), NV.NO_HIT_BG, np.uint8)
    t_[cls == 1] = NV.UNASSIGNED_BG
    t_[cls == 2] = NV.NOTVIS_BG
    rr, cc = prod["left_core_row"], prod["left_core_col"]
    t_[rr[ids > 0], cc[ids > 0]] = (170, 170, 170)
    t_[rr[ids == t], cc[ids == t]] = NEW_COL
    img.paste(Image.fromarray(t_).resize((size, size), Image.NEAREST), (1860, y + 40))
    NV.class_overlays(img, cls, 1860, y + 40, size)
    d = ImageDraw.Draw(img)
    S.text(d, (1860, y + 8), f"target {t} (blue) vs other ids (grey)", size=15, bold=True)
    fin = dd.final["stop"]["post_action_probe_of_new_target"] if dd.final else None
    if fin:
        pr_ = fin["proposal"]
        S.text(d, (1500, y + 384), f"post-action probe of {t}: {fin['label']}; next proposal "
                                   + (f"{SRC[pr_['source']][0]} local {fmt(pr_['local_gaze_deg'])}" if pr_ else "none")
                                   + f" - {SP.LABEL_NOT_EXECUTED}", size=15, bold=True, fill=NEW_COL)
    return y + 440


def panel_e(img: Image.Image, y: int, dd: Data) -> int:
    y = NV.panel_title(img, y, "E", "Controller-02 phase state (NORMAL / DEFERRED / RESIDUE); gate markers only inside "
                       "RESIDUE", [SP.LABEL_GATE_RESIDUE_ONLY, SP.LABEL_NOT_EXECUTED])
    d = ImageDraw.Draw(img)
    cols = dd.states
    x0, x1 = 240, W - 60
    cw = (x1 - x0) / max(1, len(cols))
    S.text(d, (40, y + 24), "scene phase", size=16, bold=True)
    for ci, st in enumerate(cols):
        bx = (x0 + ci * cw + 2, y + 14, x0 + (ci + 1) * cw - 2, y + 64)
        ph = st["phase"]
        fill = {"NORMAL": (232, 242, 250), "RESIDUE": (253, 236, 214), "CLOSED": (236, 236, 236)}[ph]
        d.rectangle(bx, fill=fill, outline=S.INK2, width=1)
        S.text(d, (bx[0] + 4, bx[1] + 4), ph, size=13, bold=True)
        S.text(d, (bx[0] + 4, bx[1] + 26), "initial" if st["global_step"] < 0 else f"after {st['global_step']}", size=12,
               fill=S.INK2)
    S.text(d, (40, y + 84), "172 disposition", size=16, bold=True)
    for ci, st in enumerate(cols):
        lab = st["entities"][str(SP.CONTINUING)]["status"]["label"]
        bx = (x0 + ci * cw + 2, y + 76, x0 + (ci + 1) * cw - 2, y + 116)
        tile(img, bx, lab, "")
    d = ImageDraw.Draw(img)
    S.text(d, (40, y + 136), "final-look gate", size=16, bold=True)
    for k, e in dd.gate_events:
        ci = next(i for i, st in enumerate(cols) if st["global_step"] == k)
        NV.glyph(d, x0 + (ci + 0.5) * cw, y + 146, "diamond", S.OI_VERM, r=9)
    normal_calls = sum(int((st.get("gate_guard") or {}).get("normal_calls", 0)) for st in cols)
    residue_states = [st for st in cols if st["phase"] == "RESIDUE"]
    S.text(d, (x0, y + 170), f"final-gate calls in NORMAL: {normal_calls}; RESIDUE entered: "
                             f"{'yes' if residue_states or dd.gate_events else 'no'}; gate decisions: "
                             f"{len(dd.gate_events)}; deferred events: "
                             f"{sum(1 for st in cols for e in st.get('events', []) if e['event'] == 'deferred')}",
           size=16, bold=True)
    S.text(d, (x0, y + 198), f"ordinary budget {dd.s0['budget']} own fixations; post-divergence cap "
                             f"{dd.div['cap'] if dd.div else '-'}; the full Classroom is not closed (no scene-level "
                             "closure claim)", size=15, fill=S.INK2)
    return y + 236


def overview(dd: Data) -> tuple[Image.Image, dict]:
    img = Image.new("RGB", (W, 5200), S.SURFACE)
    y = NV.header(img, "North Star-1c2 - the first scene switch under the accepted Controller-02 NORMAL / RESIDUE "
                  "semantics", [
                      "Only change vs NS1c: final_look_gate_v1 is applied in RESIDUE only. In NORMAL a ProbeResult with "
                      "an FSG6f or Cyclopean action is ACTIONABLE; at 24 own looks an ACTIONABLE object is DEFERRED.",
                      "PHYSICAL HEAD FIXED - POLICY CHART ONLY: every projection, calibration and observation stays in "
                      "canonical H0; persistent fusion in H0, target only. " + SP.LABEL_NO_NAME + ".",
                      f"Reading: {dd.outcome()}"], BADGES["overview.png"])
    y = panel_a(img, y + 6, dd)
    y = panel_b(img, y, dd)
    y = panel_c(img, y, dd)
    y = panel_d(img, y, dd)
    y = panel_e(img, y, dd)
    img = img.crop((0, 0, W, y + 20))
    return img, {"panels": ["A", "B", "C", "D", "E"], "switch_step": None if dd.switch is None else dd.switch["k"],
                 "phases_shown": dd.phases(), "gate_markers": [k for k, _e in dd.gate_events],
                 "gate_marker_phases": [next(st["phase"] for st in dd.states if st["global_step"] == k)
                                        for k, _e in dd.gate_events],
                 "scheduler_reasons_shown": [s["dec"]["scheduler_reason"] for s in dd.steps],
                 "divergence_shown": dd.div is not None, "historical_reference_shown": True}


# ------------------------------------------------------------------ the divergence figure
def divergence_fig(dd: Data) -> tuple[Image.Image, dict]:
    img = Image.new("RGB", (W, 2400), S.SURFACE)
    y = NV.header(img, "North Star-1c2 - NS1c vs NS1c2 at the same post-step-3 state", [
        "The same reconstructed state of 172 (NS1c's four measured actions, replayed), the same accepted FSG6f -> "
        "Cyclopean probe. NS1c gated the Cyclopean proposal in NORMAL service; NS1c2 does not call the gate in NORMAL.",
        "Right: where attention goes next in canonical H0 (NS1c: switch to 123; NS1c2: retain 172 at its Cyclopean "
        "fixation)."], BADGES["ns1c-vs-ns1c2-divergence.png"])
    d = ImageDraw.Draw(img)
    if dd.div is None:
        S.text(d, (50, y + 20), "no divergence record", size=S.T_BODY, bold=True)
        return img.crop((0, 0, W, y + 80)), {"divergence_shown": False}
    left, right = divergence_rows(dd)
    yl = flow(img, 50, y + 20, 980, "NS1c (NOT ACCEPTED)", left, NS1C_COL)
    yr = flow(img, 50, yl + 30, 980, "NS1c2 (accepted Controller-02 NORMAL semantics)", right, S.OI_BLUE)
    st = dd.div["state"]
    d = ImageDraw.Draw(img)
    detail = [("probe details (identical in both)", S.INK),
              f"FSG6f frontier raw {st['fsg6f']['frontier_raw_count']}, open {st['fsg6f']['frontier_open_count']}, "
              f"map-resolved {st['fsg6f']['frontier_map_resolved_count']}, boundary-resolved "
              f"{st['fsg6f']['frontier_boundary_resolved_count']}; candidates {st['fsg6f']['candidates']}",
              f"Cyclopean: {st['cyclopean']['reason']}, eligible cells {st['cyclopean']['eligible_cells']}",
              f"proposal local {fmt(st['proposal']['local_gaze_deg'])} -> H0 {fmt(st['proposal']['world_gaze_deg'], 3)}",
              f"own looks {st['own_looks']}; map {st['map_surfels']:,}; P3 calls in the probe {st['probe_P3_calls']}"]
    text_block(d, 50, yr + 10, detail, size=15, gap=25)
    # H0 sky window: 172's map, NS1c2's retained fixation, NS1c's switch target 123 and its action
    w1, h1 = 1260, 980
    im, dp = new_panel(w1, h1, "canonical H0 (yaw / pitch, degrees)", SP.LABEL_H0)
    inner = (20, 50, w1 - 20, h1 - 20)
    rec172 = dd.states[SP.PREFIX_STEPS]["entities"][str(SP.CONTINUING)] if len(dd.states) > SP.PREFIX_STEPS else None
    m172 = dd.map_of(rec172) if rec172 else np.empty((0, 3))
    n4 = dd.ns1c_step4["action"]
    m123 = dd.ns1a_map(int(n4["target"]))
    allp = np.vstack([p for p in (m172, m123) if len(p)])
    ya, pa = angles(allp)
    py_, pp_ = st["proposal"]["world_gaze_deg"]
    wy, wp = n4["world_gaze_deg"]
    ymin, ymax = min(float(ya.min()), py_, wy) - 4, max(float(ya.max()), py_, wy) + 4
    pmin, pmax = min(float(pa.min()), pp_, wp) - 4, max(float(pa.max()), pp_, wp) + 4
    for p, col in ((m172, CUR_COL), (m123, NS1C_COL)):
        if len(p):
            a, b = eq_xy(*angles(p[sub(len(p), 6000)]), inner, (ymin, ymax), (pmin, pmax))
            dots(dp, a, b, col, r=1, box=inner)
    a, b = eq_xy(np.array([py_]), np.array([pp_]), inner, (ymin, ymax), (pmin, pmax))
    S.crosshair(dp, float(a[0]), float(b[0]), r=16, color=S.OI_BLUE)
    S.text(dp, (float(a[0]) + 18, float(b[0]) - 10), "NS1c2: RETAIN 172 - Cyclopean fixation (executed next)", size=15,
           bold=True, fill=S.OI_BLUE, plate=S.WHITE)
    a2, b2 = eq_xy(np.array([wy]), np.array([wp]), inner, (ymin, ymax), (pmin, pmax))
    S.crosshair(dp, float(a2[0]), float(b2[0]), r=14, solid=False, color=NS1C_COL)
    S.text(dp, (float(a2[0]) + 18, float(b2[0]) + 6), f"NS1c: SWITCH -> {n4['target']} (gated semantics; not accepted)",
           size=15, bold=True, fill=S.INK2, plate=S.WHITE)
    S.text(dp, (24, h1 - 60), f"red: 172 map after the replayed prefix ({len(m172):,} surfels); grey: entity "
                              f"{n4['target']} (frozen NS1a seed map, display only)", size=14)
    img.paste(im, (1100, y + 20))
    yend = max(yr + 150, y + 20 + h1 + 20)
    return img.crop((0, 0, W, yend)), {"divergence_shown": True, "ns1c_switch_target": int(n4["target"]),
                                       "ns1c2_retained": SP.CONTINUING}


# ------------------------------------------------------------------ the phase timeline
def timeline(dd: Data) -> tuple[Image.Image, dict]:
    ncol = len(dd.states)
    cw = int(min(150, (W - 300) / max(1, ncol)))
    extra = [k for k in dd.deferred if k not in dd.ids]
    rows = dd.ids + extra
    rh = 50
    H = 330 + rh * len(rows) + 260
    img = Image.new("RGB", (W, H), S.SURFACE)
    y = NV.header(img, "North Star-1c2 - Controller-02 phase timeline", [
        "Rows: coherent entities (deferred identities greyed, never in the scheduler). Columns: the initial NORMAL probe "
        "and the state after each global action (prefix steps 0-3 = NS1c's measured actions, replayed).",
        "Tiles: NORMAL ACTIONABLE (blue frame) / NORMAL QUIET (check) / DEFERRED (hatched orange) / FINALIZED residual. "
        "Bold frame: current target; double arrow: switch; glyph: action source; diamond: final-look gate (RESIDUE "
        "only)."], BADGES["controller-phase-timeline.png"])
    d = ImageDraw.Draw(img)
    x0, y0 = 240, y + 90
    for ci, st in enumerate(dd.states):
        lab = "initial" if st["global_step"] < 0 else f"after {st['global_step']}"
        S.text(d, (x0 + ci * cw + 6, y0 - 82), lab, size=14, bold=True)
        ph = st["phase"]
        fill = {"NORMAL": (232, 242, 250), "RESIDUE": (253, 236, 214), "CLOSED": (236, 236, 236)}[ph]
        d.rectangle([x0 + ci * cw + 2, y0 - 58, x0 + (ci + 1) * cw - 6, y0 - 36], fill=fill, outline=S.INK2)
        S.text(d, (x0 + ci * cw + 6, y0 - 57), ph, size=12, bold=True)
        if 0 <= st["global_step"] < SP.PREFIX_STEPS:
            S.text(d, (x0 + ci * cw + 6, y0 - 32), "NS1c replay", size=11, fill=S.INK2)
    for ri, k in enumerate(rows):
        yy = y0 + ri * rh
        S.text(d, (40, yy + 12), f"{k}" + ("  (deferred id)" if k in extra else ""), size=16,
               bold=k == SP.CONTINUING, fill=S.INK2 if k in extra else dd.color.get(k, S.INK))
        for ci, st in enumerate(dd.states):
            bx = (x0 + ci * cw + 4, yy + 4, x0 + (ci + 1) * cw - 8, yy + rh - 8)
            if k in extra:
                tile(img, bx, SP.DEFERRED_STATE, "")
                continue
            lab = st["entities"][str(k)]["status"]["label"]
            tile(img, bx, lab, "")
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
        S.arrow(d, xa, ya, xb, yb, color=CUR_COL if sw else S.INK2, width=3, head=9, double=sw)
        glyph(d, x0 + ci * cw + cw / 2, yb - rh / 2 + 2, s["dec"]["action"]["source"], r=6)
    for k, _e in dd.gate_events:
        ci = next(i for i, st in enumerate(dd.states) if st["global_step"] == k)
        NV.glyph(d, x0 + ci * cw + cw / 2, y0 - 47, "diamond", S.OI_VERM, r=8)
    yy = y0 + len(rows) * rh + 20
    for ci, s in enumerate(dd.steps, start=1):
        S.text(d, (x0 + ci * cw + 4, yy), s["dec"]["scheduler_reason"][:8], size=13, bold=True)
        S.text(d, (x0 + ci * cw + 4, yy + 20), f"-> {s['dec']['action']['target']}", size=13)
    yl = yy + 60
    for src in ("fsg6f", "cyclopean_epistemic"):
        glyph(d, 50, yl + 9, src, r=7)
        S.text(d, (66, yl), f"{SRC[src][0]} action", size=15)
        yl += 26
    end = ("STOP: first executed NORMAL action on a target other than 172" if dd.final
           else (dd.terminal["outcome_reading"] if dd.terminal else ""))
    S.text(d, (400, yy + 60), end, size=17, bold=True, fill=CUR_COL if dd.final else S.INK)
    normal_calls = sum(int((st.get("gate_guard") or {}).get("normal_calls", 0)) for st in dd.states)
    S.text(d, (400, yy + 92), f"final-gate calls in NORMAL: {normal_calls}; gate decisions: {len(dd.gate_events)}",
           size=16, bold=True)
    img = img.crop((0, 0, W, yy + 140))
    return img, {"columns": ncol, "rows": rows, "deferred_shown": extra, "phases_shown": dd.phases(),
                 "gate_markers": [k for k, _e in dd.gate_events],
                 "scheduler_reasons_shown": [s["dec"]["scheduler_reason"] for s in dd.steps],
                 "sources_shown": [s["dec"]["action"]["source"] for s in dd.steps]}


# ------------------------------------------------------------------ growth 3-D
def growth_panels(img: Image.Image, y: int, dd: Data, k: int) -> int:
    rec0 = dd.s0["entities"][str(k)]
    m0 = dd.map_of(rec0)
    steps = [s for s in dd.steps if int(s["dec"]["action"]["target"]) == k]
    final = dd.map_of(dd.last["entities"][str(k)])
    n_prev = [len(m0)] + [int(s["fus"]["map_after"]) for s in steps]
    d = ImageDraw.Draw(img)
    S.text(d, (40, y), f"entity {k}: {len(m0):,} surfels at the NS1c2 start -> {len(final):,} after {len(steps)} "
                       f"action(s) ({sum(1 for s in steps if s['prefix'])} replayed NS1c, "
                       f"{sum(1 for s in steps if not s['prefix'])} new)", size=S.T_BODY, bold=True, fill=dd.color[k])
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
        segs = [(idx < n_prev[0], SEED_COL, "at the NS1c2 start")]
        for si, s_ in enumerate(steps):
            segs.append(((idx >= n_prev[si]) & (idx < n_prev[si + 1]), STEP_COLS[si % len(STEP_COLS)],
                         f"new at step {s_['k']}" + (" (NS1c)" if s_["prefix"] else "")))
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
            if not mask.any():
                continue
            dp.rectangle([bw - 330, yl + 4, bw - 318, yl + 16], fill=col)
            S.text(dp, (bw - 310, yl), f"{lab} ({int(mask.sum()):,})", size=13)
            yl += 20
        img.paste(im, (40 + i * (bw + 40), y))
    y += bh + 16
    d = ImageDraw.Draw(img)
    for s_ in steps:
        fu = s_["fus"]
        md = fu.get("matched_distance_m") or {}
        med = f"{md['median'] * 1000:.2f} mm" if md else "-"
        S.text(d, (40, y), f"step {s_['k']}{' (NS1c replay)' if s_['prefix'] else ''}: local {fmt(fu['local_gaze_deg'])} "
                           f"-> H0 {fmt(fu['world_gaze_deg'], 2)}; target points {fu['measured_points']:,}; "
                           f"{fu['action']}; matched {fu['matched']:,} (median {med}); new {fu['new']:,}; "
                           f"{fu['map_before']:,} -> {fu['map_after']:,}", size=14)
        y += 22
    return y + 20


def growth_3d(dd: Data) -> tuple[Image.Image, dict]:
    img = Image.new("RGB", (W, 4000), S.SURFACE)
    y = NV.header(img, "North Star-1c2 - multi-entity growth in canonical H0", [
        "Persistent maps in canonical H0 (fixed head at the origin, baseline on +X); the start map and the surfels each "
        "action added (target-only 12-mm fusion).", "PHYSICAL HEAD FIXED - POLICY CHART ONLY."],
                  BADGES["multi-entity-growth-3d.png"])
    shown = [SP.CONTINUING] + ([int(dd.switch["dec"]["action"]["target"])] if dd.switch is not None else [])
    for k in shown:
        y = growth_panels(img, y + 10, dd, k)
    if dd.switch is None:
        S.text(ImageDraw.Draw(img), (40, y), "no second entity was attended", size=S.T_BODY, bold=True)
        y += 40
    return img.crop((0, 0, W, y + 10)), {"entities": shown}


# ------------------------------------------------------------------ controller vs North-Star support
def support(dd: Data) -> tuple[Image.Image, dict]:
    diag = dd.ctx["diagnostics"]
    bars = []
    for k in dd.ids:
        dg = diag[str(k)]
        bars.append({"label": f"{k} init", "ctrl": dg["controller_state_target_support"],
                     "ns": dg["ns1a_initialization_look_target_points"], "kind": "init"})
    nb = diag[str(SP.CONTINUING)].get("ns1b_action_look")
    if nb:
        bars.append({"label": "172 NS1b", "ctrl": nb["controller_state_target_support"],
                     "ns": nb["north_star_target_points"], "kind": "ns1b"})
    for s in dd.steps:
        bars.append({"label": f"s{s['k']} ({s['dec']['action']['target']})",
                     "ctrl": s["upd"]["controller_state_target_support"], "ns": s["upd"]["north_star_target_points"],
                     "kind": "prefix" if s["prefix"] else "action"})
    H = 1250
    img = Image.new("RGB", (W, H), S.SURFACE)
    y = NV.header(img, "North Star-1c2 - controller-state support vs North-Star measurement (descriptive)", [
        "Per look: the accepted Classroom matcher's valid target support (controller observation state, planar rectified "
        "core) vs the North-Star raw-core PERFECT spherical target points.",
        "Descriptive only (rank-1 zero controller-state support retained, not fixed)."],
                  BADGES["controller-vs-northstar-support.png"])
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = 120, y + 40, W - 60, H - 170
    vmax = max(1, max(max(b["ctrl"], b["ns"]) for b in bars))
    d.line([x0, y1, x1, y1], fill=S.INK, width=2)
    d.line([x0, y0, x0, y1], fill=S.INK, width=2)
    for tv in np.linspace(0, vmax, 6):
        yy = y1 - (y1 - y0) * tv / vmax
        d.line([x0 - 6, yy, x1, yy], fill=S.GRID, width=1)
        S.text(d, (x0 - 100, yy - 10), f"{int(tv):,}", size=14, fill=S.INK2)
    n = len(bars)
    gw = (x1 - x0 - 20) / max(1, n)
    bw = max(4.0, gw * 0.36)
    for i, b in enumerate(bars):
        gx = x0 + 10 + i * gw
        for j_, (v, col, hatch) in enumerate(((b["ctrl"], S.OI_ORANGE, True), (b["ns"], S.OI_BLUE, False))):
            bx = [gx + j_ * (bw + 3), y1 - (y1 - y0) * v / vmax, gx + j_ * (bw + 3) + bw, y1]
            d.rectangle(bx, fill=col)
            if hatch and bx[3] - bx[1] > 6:
                S.hatch(img, [int(c) for c in bx], S.WHITE, spacing=8, width=2)
                d = ImageDraw.Draw(img)
        S.text(d, (gx, y1 + 8 + 18 * (i % 2)), b["label"], size=11, fill=S.INK if b["kind"] == "action" else S.INK2,
               bold=b["kind"] == "action")
    d.rectangle([x0, H - 110, x0 + 20, H - 92], fill=S.OI_ORANGE)
    S.hatch(img, [x0, H - 110, x0 + 20, H - 92], S.WHITE, spacing=8, width=2)
    d = ImageDraw.Draw(img)
    S.text(d, (x0 + 30, H - 112), "controller-state target support (matcher-valid target points)", size=15)
    d.rectangle([x0 + 700, H - 110, x0 + 720, H - 92], fill=S.OI_BLUE)
    S.text(d, (x0 + 730, H - 112), "North-Star raw-core target metric points (PERFECT, spherical)", size=15)
    return img, {"bars": len(bars), "actions": len(dd.steps)}


FIGURE_FUNCS = {"overview.png": overview, "ns1c-vs-ns1c2-divergence.png": divergence_fig,
                "controller-phase-timeline.png": timeline, "multi-entity-growth-3d.png": growth_3d,
                "controller-vs-northstar-support.png": support}


def render_all(run: Path) -> tuple[dict, Data]:
    dd = Data(Path(run))
    return {n: fn(dd) for n, fn in FIGURE_FUNCS.items()}, dd


def visualize(run: Path, vis: Path) -> dict:
    vis = Path(vis)
    vis.mkdir(parents=True, exist_ok=True)
    figs, dd = render_all(run)
    man = {"schema": "NS1c2-visuals-v1", "visual_language": "Visual Language 1", "run": str(run),
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
