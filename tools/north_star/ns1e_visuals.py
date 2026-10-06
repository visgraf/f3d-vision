"""North Star-1e: the scientific visuals (Visual Language 1; deterministic PNGs) and the PLY exports.

Contract: docs/north-star/ns1e-coherent-full-loop-m2-memory-contract.md, section 28.

- ``overview.png``: A start state; B full attention timeline; C map + memory growth; D reactivations; E terminal state;
  F post-freeze coverage (persistent map; effective geometry separately; 98.34 % only as a non-comparable reference).
- ``controller-full-timeline.png``, ``multi-entity-final-geometry.png``, ``memory-flow-timeline.png``,
  ``coverage-by-entity.png``, ``rank1-diagnostic.png``; ``natural-reactivation.png`` / ``residue-phase.png`` when they
  occurred.
- ``final-coherent-persistent-points.ply`` (the ten persistent maps only) and the labelled
  ``final-effective-geometry-diagnostic.ply``.

Reads only the NS1e run (and the accepted maps / patches its records name).  No catalog, no name.
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
for _p in (HERE, HERE.parent, HERE.parent / "visual_language", HERE.parents[1]):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import ns1a_visuals as NV  # noqa: E402  (accepted NS1a drawing helpers; its Data class is never used)
import ns1b_visuals as BV  # noqa: E402  (accepted NS1b drawing helpers; its Data class is never used)
import ns1e_core as CORE  # noqa: E402
import ns1e_spec as SP  # noqa: E402
import style as S  # noqa: E402  (Visual Language 1, read-only)

ORA, DER, REF = SP.TRUTH_ORACLE, SP.TRUTH_DERIVED, SP.TRUTH_REFERENCE
W = NV.W
COMMON = [SP.LABEL_FIXED_HEAD, SP.LABEL_MAP, SP.LABEL_MEMORY, SP.LABEL_NO_NAME]
BADGES = {"overview.png": [ORA, DER, REF], "controller-full-timeline.png": [DER],
          "multi-entity-final-geometry.png": [ORA, DER], "memory-flow-timeline.png": [DER],
          "coverage-by-entity.png": [DER, REF], "rank1-diagnostic.png": [ORA, DER],
          "natural-reactivation.png": [DER], "residue-phase.png": [DER]}
LABELS = {"overview.png": [SP.LABEL_ORACLE_CORR, SP.LABEL_GEOMETRY, SP.LABEL_SEGMENTATION, SP.LABEL_AMBIGUOUS,
                           SP.LABEL_SCHEDULER, SP.LABEL_GATE_RESIDUE_ONLY, SP.LABEL_EFFECTIVE, SP.LABEL_EFFECTIVE_DIAG,
                           SP.LABEL_NON_COMPARABLE, SP.LABEL_REFERENCE, SP.LABEL_BOOTSTRAP, SP.LABEL_H0] + COMMON,
          "controller-full-timeline.png": [SP.LABEL_SCHEDULER, SP.LABEL_GATE_RESIDUE_ONLY],
          "multi-entity-final-geometry.png": [SP.LABEL_MAP, SP.LABEL_H0, SP.LABEL_FIXED_HEAD, SP.LABEL_NO_NAME],
          "memory-flow-timeline.png": [SP.LABEL_MEMORY, SP.LABEL_AMBIGUOUS, SP.LABEL_MAP],
          "coverage-by-entity.png": [SP.LABEL_REFERENCE, SP.LABEL_MAP, SP.LABEL_EFFECTIVE_DIAG, SP.LABEL_NON_COMPARABLE],
          "rank1-diagnostic.png": [SP.LABEL_GEOMETRY, SP.LABEL_SEGMENTATION],
          "natural-reactivation.png": [SP.LABEL_MEMORY],
          "residue-phase.png": [SP.LABEL_GATE_RESIDUE_ONLY]}
PALETTE = [S.OI_BLUE, S.OI_VERM, S.OI_GREEN, S.OI_PURPLE, S.OI_ORANGE, S.WINE, S.OI_SKY, S.REF_BROWN,
           (90, 90, 90), S.CORE_GREEN]
GLYPHS = ["circle", "square", "triangle", "diamond", "down", "hex", "circle", "square", "triangle", "diamond"]
SOURCE_GLYPH = {"fsg6f": "circle", "cyclopean_epistemic": "triangle"}
AMBIG_COL = (196, 192, 184)

j, npz, sub, dots, text_block = BV.j, BV.npz, BV.sub, BV.dots, BV.text_block


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fmt(v, nd=1) -> str:
    return "-" if v is None else f"({v[0]:+.{nd}f}, {v[1]:+.{nd}f})"


def ent_style(i: int, ids: list[int]) -> tuple[tuple, str]:
    n = ids.index(int(i))
    return PALETTE[n % len(PALETTE)], GLYPHS[n % len(GLYPHS)]


class Data:
    def __init__(self, run: Path) -> None:
        self.run = Path(run)
        self.initial = j(self.run / SP.scene_state_rel("initial"))
        self.ids = [int(i) for i in self.initial["scene_ids"]]
        self.handoff = j(self.run / "handoff/handoff.json")
        self.cap = j(self.run / "handoff/cap.json")
        self.charts = j(self.run / "handoff/charts.json")["charts"]
        self.terminal = j(self.run / "scene/terminal.json") if (self.run / "scene/terminal.json").exists() else None
        self.cm = j(self.run / "control/control-manifest.json") if (self.run / "control/control-manifest.json").exists() \
            else None
        self.ev = j(self.run / "evaluation/evaluation.json") if (self.run / "evaluation/evaluation.json").exists() else None
        k0 = int(self.initial["next_global_step"])
        self.steps = []
        k = k0
        while (self.run / SP.checkpoint_rel(k)).exists():
            self.steps.append(k)
            k += 1
        self.k0 = k0
        self.dec = {k: j(self.run / SP.step_dir(k) / "plan/decision.json") for k in self.steps}
        self.fus = {k: j(self.run / SP.step_dir(k) / "fusion/fusion.json") for k in self.steps}
        self.mem = {k: j(self.run / SP.step_dir(k) / "memory/event.json") for k in self.steps}
        self.upd = {k: j(self.run / SP.step_dir(k) / "update/update.json") for k in self.steps}
        self.final = j(self.run / SP.state_after(self.steps[-1])) if self.steps else self.initial
        self.events = []
        for k in self.steps:
            self.events += j(self.run / SP.state_after(k))["events"]
        if self.terminal is not None:
            self.events += list(self.terminal.get("events_in_decide") or [])

    def map_xyz(self, rec: dict) -> np.ndarray:
        return np.asarray(npz(CORE.resolve(rec["map"]["path"], self.run))["xyz_h"], np.float64)

    def map_rgb(self, rec: dict) -> np.ndarray:
        return np.asarray(npz(CORE.resolve(rec["map"]["path"], self.run))["rgb"], np.float64)

    def outcome(self) -> dict:
        if self.terminal is None:
            return {"outcome": "running", "scope": "-", "statement": "the control loop has not terminated"}
        return self.terminal["outcome"]

    def statuses(self) -> dict:
        if self.terminal is not None:
            return self.terminal["statuses_after_decide"]
        return {k: v["status"] for k, v in self.final["entities"].items()}

    def ledger(self):
        return CORE.rebuild_ledger(self.final["memory"]["events"], self.run)


def scope_label(dd: Data) -> str:
    oc = dd.outcome()
    return oc.get("scope", "-")


# ------------------------------------------------------------------ shared panels
def sky_points(d, box, dd: Data, ents: dict, nmax: int = 2500, faded: bool = False) -> None:
    for i in dd.ids:
        rec = ents[str(i)]
        xyz = dd.map_xyz(rec)
        if not len(xyz):
            continue
        y, p = BV.angles(xyz[sub(len(xyz), nmax)])
        u, v = BV.eq_xy(y, p, box)
        col, _g = ent_style(i, dd.ids)
        if faded:
            col = tuple(int(c + (255 - c) * 0.55) for c in col)
        dots(d, u, v, col, r=1, box=box)


def entity_labels(d, box, dd: Data, ents: dict) -> None:
    """A glyph at each map's median direction and a leader line to a label placed clear of the others."""
    placed: list[tuple[float, float]] = []
    for i in dd.ids:
        xyz = dd.map_xyz(ents[str(i)])
        if not len(xyz):
            continue
        y, p = BV.angles(np.median(xyz, axis=0)[None])
        u, v = (float(np.atleast_1d(a)[0]) for a in BV.eq_xy(y, p, box))
        col, g = ent_style(i, dd.ids)
        lx, ly = u + 16, v - 10
        while any(abs(lx - a) < 46 and abs(ly - b) < 20 for a, b in placed):
            ly += 21
        placed.append((lx, ly))
        if abs(ly - (v - 10)) > 1:
            d.line([u, v, lx - 2, ly + 9], fill=S.INK2, width=1)
        NV.glyph(d, u, v, g, col, r=8)
        S.text(d, (lx, ly), str(i), size=16, bold=True)


def clusters(dd: Data, ents: dict, gap_deg: float = 40.0) -> list[dict]:
    """Entities grouped by H0 yaw (a gap of more than ``gap_deg`` starts a new group), each with a padded yaw / pitch
    extent (2-98 % of its map points, wrap-safe around its centre yaw)."""
    rows = []
    for i in dd.ids:
        xyz = dd.map_xyz(ents[str(i)])
        if not len(xyz):
            continue
        y, p = BV.angles(xyz[sub(len(xyz), 3000)])
        c = float(np.degrees(np.arctan2(np.sin(np.radians(y)).mean(), np.cos(np.radians(y)).mean())))
        rows.append((c, i, y, p))
    rows.sort()
    groups, cur = [], []
    for r in rows:
        if cur and abs(((r[0] - cur[-1][0] + 180) % 360) - 180) > gap_deg:
            groups.append(cur)
            cur = []
        cur.append(r)
    if cur:
        groups.append(cur)
    out = []
    for gr in groups:
        c = float(np.mean([r[0] for r in gr]))
        ys = np.concatenate([((r[2] - c + 180) % 360) - 180 + c for r in gr])
        ps = np.concatenate([r[3] for r in gr])
        out.append({"ids": [r[1] for r in gr], "centre": c,
                    "yaw": (float(np.percentile(ys, 1)) - 6, float(np.percentile(ys, 99)) + 6),
                    "pitch": (max(-90.0, float(np.percentile(ps, 1)) - 6), min(90.0, float(np.percentile(ps, 99)) + 6))})
    return out


def zoom_frame(img, box, title, ext):
    """A zoomed equirectangular H0 panel with the box's aspect ratio; returns (inner, yrange, prange, centre)."""
    BV.sky(img, box, title, SP.LABEL_H0)
    d = ImageDraw.Draw(img)
    inner = (box[0] + 10, box[1] + 46, box[2] - 10, box[3] - 30)
    (y0, y1), (p0, p1) = ext["yaw"], ext["pitch"]
    w, h = inner[2] - inner[0], inner[3] - inner[1]
    span = max((y1 - y0) / w, (p1 - p0) / h)
    cy, cp = (y0 + y1) / 2, (p0 + p1) / 2
    yr, pr = (cy - span * w / 2, cy + span * w / 2), (cp - span * h / 2, cp + span * h / 2)
    step = 10 if span * w > 40 else 5
    for yy in np.arange(math.ceil(yr[0] / step) * step, yr[1], step):
        u, _ = BV.eq_xy(yy, 0, inner, yr, pr)
        d.line([float(np.asarray(u)), inner[1], float(np.asarray(u)), inner[3]], fill=S.GRID, width=1)
    for pp in np.arange(math.ceil(pr[0] / step) * step, pr[1], step):
        _, v = BV.eq_xy(0, pp, inner, yr, pr)
        d.line([inner[0], float(np.asarray(v)), inner[2], float(np.asarray(v))], fill=S.GRID, width=1)
    S.text(d, (box[0] + 12, box[3] - 26), f"yaw {((yr[0] + 180) % 360) - 180:+.0f}..{((yr[1] + 180) % 360) - 180:+.0f} "
                                          f"deg, pitch {pr[0]:+.0f}..{pr[1]:+.0f} deg (grid {step} deg)", size=14,
           fill=S.INK2)
    return inner, yr, pr, cy


def zoom_points(d, inner, yr, pr, c, dd: Data, ents: dict, ids, nmax=4000, faded=False, labels=True):
    placed = []
    for i in ids:
        xyz = dd.map_xyz(ents[str(i)])
        if not len(xyz):
            continue
        y, p = BV.angles(xyz[sub(len(xyz), nmax)])
        y = ((y - c + 180) % 360) - 180 + c
        u, v = BV.eq_xy(y, p, inner, yr, pr)
        col, g = ent_style(i, dd.ids)
        if faded:
            col = tuple(int(cc + (255 - cc) * 0.55) for cc in col)
        dots(d, u, v, col, r=1, box=inner)
        if labels:
            ym, pm = BV.angles(np.median(xyz, axis=0)[None])
            ym = ((ym - c + 180) % 360) - 180 + c
            um, vm = (float(np.atleast_1d(a)[0]) for a in BV.eq_xy(ym, pm, inner, yr, pr))
            lx, ly = um + 16, vm - 10
            while any(abs(lx - a) < 46 and abs(ly - b) < 20 for a, b in placed):
                ly += 21
            placed.append((lx, ly))
            if abs(ly - (vm - 10)) > 1:
                d.line([um, vm, lx - 2, ly + 9], fill=S.INK2, width=1)
            NV.glyph(d, um, vm, g, col, r=8)
            S.text(d, (lx, ly), str(i), size=16, bold=True)


def h0_frame(img, box, title):
    BV.sky(img, box, title, SP.LABEL_H0)
    d = ImageDraw.Draw(img)
    inner = (box[0] + 10, box[1] + 46, box[2] - 10, box[3] - 10)
    for yy in range(-180, 181, 45):
        u, _ = BV.eq_xy(yy, 0, inner)
        d.line([float(np.asarray(u)), inner[1], float(np.asarray(u)), inner[3]], fill=S.GRID, width=1)
    for pp in range(-90, 91, 30):
        _, v = BV.eq_xy(0, pp, inner)
        d.line([inner[0], float(np.asarray(v)), inner[2], float(np.asarray(v))], fill=S.GRID, width=1)
    return inner


def panel_a(img: Image.Image, y: int, dd: Data) -> int:
    h = dd.handoff
    nxt = h["next_decision"]
    y = NV.panel_title(img, y, "A", "Start state: the accepted post-NS1c2 scene + the accepted NS1d M2 memory (events 0-8)",
                       [SP.LABEL_H0, "NS1d ACCEPTED"])
    groups = clusters(dd, dd.initial["entities"])
    gw = 1200 // max(1, len(groups))
    for n_, gr in enumerate(groups):
        box = (40 + n_ * gw, y, 40 + (n_ + 1) * gw - 10, y + 640)
        inner, yr, pr, c = zoom_frame(img, box, f"H0 zoom {n_ + 1}", gr)
        d = ImageDraw.Draw(img)
        zoom_points(d, inner, yr, pr, c, dd, dd.initial["entities"], gr["ids"])
        if 202 in gr["ids"]:
            wy = ((nxt["world_gaze_deg"][0] - c + 180) % 360) - 180 + c
            u, v = (float(np.atleast_1d(a)[0]) for a in BV.eq_xy(wy, nxt["world_gaze_deg"][1], inner, yr, pr))
            S.crosshair(d, u, v, r=18, solid=False, color=S.OI_VERM)
            S.text(d, (u + 20, v + 14), "next action (202)", size=16, bold=True, fill=S.OI_VERM)
    d = ImageDraw.Draw(img)
    tx = 1280
    rows = [("entity  looks  map     memory own / cross   revision          state       next proposal", S.INK)]
    for r in dd.initial["table"]:
        mem = r["memory"]
        prop = r.get("proposal") or {}
        rows.append(f"{r['temporary_entity_id']:>5}  {r['own_looks']:>4}  {r['map_surfels']:>6,}  "
                    f"{mem['own_memory_points']:>8,} / {mem['cross_memory_points']:<7,}  "
                    f"{str(r['revision']):<16}  {r['label']:<10}  "
                    f"{(prop.get('source') or '-')[:9]} {fmt(prop.get('local_gaze_deg'))}")
    d.rectangle([tx - 10, y, W - 40, y + 640], fill=S.PANEL, outline=S.FAINT, width=2)
    yy = text_block(d, tx, y + 14, rows, size=16, gap=27)
    lines = [("accepted NS1d M2 memory: " + f"{h['memory_total']:,} samples in {len(h['memory_ids'])} observed ids "
              "(controller-phase events 0-8 only)", S.INK),
             f"current target 202 (bout 2, global step 8); 172 QUIET since step {h['quiet_since'].get('172')}",
             f"next (reproduced exactly before any render): retain 202, {nxt['source']} local {fmt(nxt['local_gaze_deg'])}"
             f" -> H0 ({nxt['world_gaze_deg'][0]:.3f}, {nxt['world_gaze_deg'][1]:.3f})",
             f"derived hard cap: {dd.cap['max_new_physical_actions']} new actions (absolute step "
             f"{dd.cap['absolute_action_cap']}); {SP.LABEL_BOOTSTRAP}",
             f"ids 10 / 110 / 178: {SP.LABEL_AMBIGUOUS} (stored in memory, never scheduled)"]
    text_block(d, tx, yy + 14, lines, size=16, gap=28)
    return y + 660


def timeline_grid(img, d, box, dd: Data, compact: bool) -> dict:
    """Entity rows x global step; one glyph per action (FSG6f circle / Cyclopean triangle / final residue square),
    switches, natural reactivations, quiet / deferred / finalized events."""
    x0, y0, x1, y1 = box
    ids = dd.ids
    k_last = (dd.steps[-1] if dd.steps else dd.k0) + (1 if dd.terminal is not None else 0)
    nst = max(1, k_last - dd.k0 + 1)
    lab_w = 120
    cw = (x1 - x0 - lab_w) / nst
    rh = (y1 - y0 - 40) / len(ids)

    def xs(k):
        return x0 + lab_w + (k - dd.k0 + 0.5) * cw

    def ys(i):
        return y0 + 30 + (ids.index(int(i)) + 0.5) * rh
    d.rectangle(box, fill=S.PANEL, outline=S.FAINT, width=2)
    for n, i in enumerate(ids):
        col, g = ent_style(i, ids)
        NV.glyph(d, x0 + 20, ys(i), g, col, r=7)
        S.text(d, (x0 + 36, ys(i) - 10), f"{i}" + ("*" if i in SP.RANK1 else ""), size=16, bold=True)
        d.line([x0 + lab_w, ys(i), x1 - 6, ys(i)], fill=S.GRID, width=1)
    tick = 10 if nst > 60 else 5 if nst > 20 else 1
    for k in range(dd.k0, k_last + 1):
        if (k - dd.k0) % tick == 0:
            S.text(d, (xs(k) - 8, y0 + 4), str(k), size=13, fill=S.INK2)
    counts = {"fsg6f": 0, "cyclopean_epistemic": 0, "final_residue": 0, "switches": 0, "natural_reactivation_switches": 0}
    prev = int(dd.initial["current"])
    for k in dd.steps:
        dec = dd.dec[k]
        t, src = int(dec["action"]["target"]), dec["action"]["source"]
        col = S.OI_VERM if dec["kind"] == "final_residue" else S.OI_BLUE
        if t != prev:
            counts["switches"] += 1
            d.line([xs(k) - cw / 2, ys(prev), xs(k) - cw / 2, ys(t)], fill=S.MUTED, width=1)
            if dec["scheduler_reason"] == "natural_reactivation":
                counts["natural_reactivation_switches"] += 1
                S.text(d, (xs(k) - 6, ys(t) - 26), "R", size=14, bold=True, fill=S.OI_GREEN)
        prev = t
        if dec["kind"] == "final_residue":
            counts["final_residue"] += 1
            NV.glyph(d, xs(k), ys(t), "square", col, r=max(3, min(7, cw / 2.2)))
        else:
            counts[src] += 1
            NV.glyph(d, xs(k), ys(t), SOURCE_GLYPH[src], col, r=max(3, min(7, cw / 2.2)),
                     hollow=src == "cyclopean_epistemic")
    marks = {"quiet": ("Q", S.SLATE), "deferred": ("D", S.OI_ORANGE), "finalized": ("F", S.INK),
             "natural_reactivation": ("R", S.OI_GREEN)}
    for e in dd.events:
        if e["event"] not in marks or int(e["object"]) not in ids:
            continue
        k = int(e["global_step"])
        s_, c_ = marks[e["event"]]
        S.text(d, (xs(k) + 2, ys(int(e["object"])) + 4), s_, size=13 if compact else 15, bold=True, fill=c_)
    if dd.terminal is not None:
        k = int(dd.terminal["global_step"])
        d.line([xs(k), y0 + 26, xs(k), y1 - 4], fill=S.INK, width=3)
        S.text(d, (xs(k) - 60, y1 - 26), dd.terminal["kind"].upper(), size=15, bold=True)
    for ph in (dd.final["machine"]["phases"] if dd.terminal is None else dd.terminal["machine_after_decide"]["phases"]):
        if ph["phase"] == "RESIDUE":
            k = int(ph["from_global_step"])
            S.dashed_line(d, [(xs(k) - cw / 2, y0 + 26), (xs(k) - cw / 2, y1 - 4)], S.OI_VERM, width=2)
            lx = xs(k) - cw / 2 + 4
            if lx + 80 > x1:
                lx = xs(k) - cw / 2 - 84
            S.text(d, (lx, y0 + 26), "RESIDUE", size=14, bold=True, fill=S.OI_VERM)
    return counts


def legend_row(d, x, y) -> None:
    items = [("circle", S.OI_BLUE, False, "FSG6f action (NORMAL)"), ("triangle", S.OI_BLUE, True,
                                                                     "Cyclopean action (NORMAL)"),
             ("square", S.OI_VERM, False, "final residue observation (RESIDUE)")]
    for g, c, hol, lab in items:
        NV.glyph(d, x + 8, y + 12, g, c, r=7, hollow=hol)
        S.text(d, (x + 22, y), lab, size=15)
        x += d.textlength(lab, font=S.font(15)) + 60
    for s_, c_, lab in (("Q", S.SLATE, "QUIET"), ("D", S.OI_ORANGE, "DEFERRED"), ("F", S.INK, "FINALIZED"),
                        ("R", S.OI_GREEN, "natural reactivation"), ("*", S.INK, "rank-1 entity")):
        S.text(d, (x, y), s_, size=15, bold=True, fill=c_)
        S.text(d, (x + 18, y), lab, size=15)
        x += d.textlength(lab, font=S.font(15)) + 50


def panel_b(img: Image.Image, y: int, dd: Data) -> tuple[int, dict]:
    y = NV.panel_title(img, y, "B", "Full attention timeline: target x global action (accepted Controller-02)",
                       [SP.LABEL_SCHEDULER, SP.LABEL_GATE_RESIDUE_ONLY])
    d = ImageDraw.Draw(img)
    counts = timeline_grid(img, d, (40, y, W - 40, y + 470), dd, compact=True)
    legend_row(d, 50, y + 480)
    nf = sum(1 for k in dd.steps if dd.dec[k]["action"]["source"] == "fsg6f")
    S.text(d, (50, y + 512), f"{len(dd.steps)} new physical actions (steps {dd.k0}..{dd.steps[-1] if dd.steps else '-'}); "
                             f"FSG6f {counts['fsg6f']}, Cyclopean {counts['cyclopean_epistemic']}, final residue "
                             f"{counts['final_residue']}; switches {counts['switches']} (natural-reactivation switches "
                             f"{counts['natural_reactivation_switches']}); NORMAL gate calls 0", size=16, bold=True)
    counts["fsg6f_check"] = nf
    return y + 550, counts


def log_bar(d, x, y, w, h, value, vmax, col, hatch_img=None, label=""):
    if value <= 0:
        return x
    frac = math.log10(1 + value) / math.log10(1 + vmax)
    x1 = x + w * frac
    d.rectangle([x, y, x1, y + h], fill=col)
    if label:
        S.text(d, (x1 + 6, y - 2), label, size=14)
    return x1


def panel_c(img: Image.Image, y: int, dd: Data) -> tuple[int, dict]:
    y = NV.panel_title(img, y, "C", "Map + memory growth per entity", ["persistent map != measurement memory",
                                                                          "memory samples NOT fused"])
    d = ImageDraw.Draw(img)
    fin, ini = dd.final["entities"], dd.initial["entities"]
    vmax = max(max(e["memory"]["effective_points"] for e in fin.values()), 10)
    rh = 64
    S.text(d, (60, y), "bars on a log10(1 + n) scale; numbers exact", size=15, fill=S.INK2)
    yy = y + 28
    out = {}
    for i in dd.ids:
        a, b = ini[str(i)], fin[str(i)]
        col, g = ent_style(i, dd.ids)
        NV.glyph(d, 70, yy + 22, g, col, r=8)
        S.text(d, (88, yy + 10), f"{i}" + (" (rank 1)" if i in SP.RANK1 else ""), size=17, bold=True)
        x0, bw = 330, 1100
        log_bar(d, x0, yy + 4, bw, 12, b["map"]["surfels"], vmax, S.GEOM_FAR)
        log_bar(d, x0, yy + 4, bw, 12, a["map"]["surfels"], vmax, S.GEOM_NEAR)
        log_bar(d, x0, yy + 22, bw, 12, b["memory"]["own_memory_points"], vmax, S.OI_VERM)
        log_bar(d, x0, yy + 40, bw, 12, b["memory"]["cross_memory_points"], vmax, S.OI_BLUE)
        S.text(d, (x0 + bw + 30, yy + 2), f"map {a['map']['surfels']:,} -> {b['map']['surfels']:,} surfels   "
                                           f"own memory {b['memory']['own_memory_points']:,}   cross-target "
                                           f"{b['memory']['cross_memory_points']:,}   effective "
                                           f"{b['memory']['effective_points']:,}", size=15)
        S.text(d, (x0 + bw + 30, yy + 26), f"own looks {a['own_looks']} -> {b['own_looks']}; revision "
                                            f"{a['revision']} -> {b['revision']}", size=15, fill=S.INK2)
        out[str(i)] = {"map": [a["map"]["surfels"], b["map"]["surfels"]], "own": b["memory"]["own_memory_points"],
                       "cross": b["memory"]["cross_memory_points"], "effective": b["memory"]["effective_points"]}
        yy += rh
    leg = [(S.GEOM_NEAR, "initial persistent map"), (S.GEOM_FAR, "final persistent map (fused, target-only)"),
           (S.OI_VERM, "own memory samples (NOT fused)"), (S.OI_BLUE, "cross-target memory samples (NOT fused)")]
    x = 60
    for c, lab in leg:
        d.rectangle([x, yy + 6, x + 26, yy + 20], fill=c)
        S.text(d, (x + 34, yy), lab, size=15)
        x += d.textlength(lab, font=S.font(15)) + 70
    return yy + 40, out


def panel_d(img: Image.Image, y: int, dd: Data) -> tuple[int, int]:
    reacts = [r for k in dd.steps for r in (dd.upd[k].get("natural_reactivations") or [])]
    y = NV.panel_title(img, y, "D", "Natural reactivations (revision -> cache invalidation -> re-probe; no manual call)",
                       [SP.LABEL_MEMORY])
    d = ImageDraw.Draw(img)
    if not reacts:
        S.text(d, (60, y + 10), SP.LABEL_NO_REACTIVATION, size=S.T_HEAD, bold=True)
        S.text(d, (60, y + 52), "no QUIET entity received a revision change that turned its probe ACTIONABLE",
               size=S.T_SMALL, fill=S.INK2)
        return y + 90, 0
    yy = y + 6
    for r in reacts[:8]:
        served = [k for k in dd.steps if int(dd.dec[k]["action"]["target"]) == r["object"] and k > r["global_step"]]
        S.text(d, (60, yy), f"{r['object']}: QUIET since step {r.get('quiet_since_step')}; step {r['global_step']} "
                            f"(target {r['triggering_target']}, memory event {r['memory_event']}) added "
                            f"{r['cross_target_points_added']:,} samples of {r['object']}; revision "
                            f"{r['revision_before']} -> {r['revision_after']}; effective "
                            f"{r['effective_points_before']:,} -> {r['effective_points_after']:,}; next proposal "
                            f"{(r.get('next_proposal') or {}).get('source')} "
                            f"{fmt((r.get('next_proposal') or {}).get('local_gaze_deg'))}; later served: "
                            f"{'step ' + str(served[0]) if served else 'no'}", size=16)
        yy += 30
    if len(reacts) > 8:
        S.text(d, (60, yy), f"... {len(reacts) - 8} more (natural-reactivation.png)", size=16, fill=S.INK2)
        yy += 30
    return yy + 10, len(reacts)


def tile_state(st: dict) -> str:
    if st["disposition"] == "DEFERRED":
        return "DEFERRED"
    if st["disposition"] == "FINALIZED" and st["local"] != "QUIET":
        return "RESIDUAL"
    return st["local"] if st["local"] in ("QUIET", "ACTIONABLE", "SEEDABLE", "UNLOCATED") else "QUIET"


def panel_e(img: Image.Image, y: int, dd: Data) -> tuple[int, dict]:
    oc = dd.outcome()
    gen = "-" if dd.terminal is None else ("scene_closed" if dd.terminal["kind"] == "closed" else "CapReached")
    y = NV.panel_title(img, y, "E", f"Terminal state: Controller-02 {gen}  ->  scientific label {oc.get('scope')}",
                       ["Outcome " + str(oc.get("outcome"))])
    d = ImageDraw.Draw(img)
    sts = dd.statuses()
    fin = dd.final["entities"]
    tw, th = 215, 120
    for n, i in enumerate(dd.ids):
        st = sts[str(i)]
        x = 50 + n * (tw + 12)
        S.state_tile(img, (x, y + 8, x + tw, y + 8 + th), tile_state(st), str(i), size=S.T_BODY)
        d = ImageDraw.Draw(img)
        S.text(d, (x + 4, y + th + 16), f"{st['local']}/{st['disposition']}", size=13, bold=True)
        S.text(d, (x + 4, y + th + 36), f"{st['reason'] or '-'}"[:28], size=13, fill=S.INK2)
        S.text(d, (x + 4, y + th + 56), f"looks {fin[str(i)]['own_looks']}", size=13, fill=S.INK2)
    bd = (dd.terminal or {}).get("terminal_breakdown") or {}
    lines = [(oc.get("statement", ""), S.INK),
             "QUIET NORMAL: " + str(bd.get("quiet_normal", "-")) + ";  FINALIZED quiet-before-final-probe: "
             + str(bd.get("finalized_quiet_before_final_probe", "-")) + ";  FINALIZED final-probe-rejected: "
             + str(bd.get("finalized_final_probe_rejected", "-")),
             "FINALIZED final-probe-executed but still ACTIONABLE: "
             + str(bd.get("finalized_final_probe_executed_still_actionable", "-")) + ";  other residual: "
             + str(bd.get("other_residual", "-")),
             f"Controller-02 scene_closed != all objects quiet; the universe is the ten coherent ids only "
             f"({SP.SCOPE_CLOSED}), never a full-Classroom closure"]
    text_block(d, 50, y + th + 90, lines, size=16, gap=28)
    return y + th + 210, {"generic": gen, "scope": oc.get("scope"), "outcome": oc.get("outcome")}


def coverage_bars(img, d, x, y, w, dd: Data, rowh=48) -> int:
    ev = dd.ev
    for i in dd.ids:
        r = ev["per_entity"][str(i)]
        col, g = ent_style(i, dd.ids)
        NV.glyph(d, x + 10, y + 16, g, col, r=7)
        S.text(d, (x + 26, y + 4), str(i), size=16, bold=True)
        bx = x + 110
        d.rectangle([bx, y + 4, bx + w, y + 18], outline=S.FAINT, width=1)
        d.rectangle([bx, y + 24, bx + w, y + 38], outline=S.FAINT, width=1)
        if r["status"] == SP.NO_REFERENCE:
            S.text(d, (bx + 8, y + 4), SP.NO_REFERENCE, size=14, bold=True, fill=S.INK2)
        else:
            d.rectangle([bx, y + 4, bx + w * r["coverage_fraction_weighted"], y + 18], fill=S.OI_GREEN)
            S.hatch(img, (bx, y + 24, int(bx + w * r["effective_coverage_fraction_weighted"]), y + 38), S.OI_SKY,
                    spacing=6, width=2)
            d = ImageDraw.Draw(img)
            S.text(d, (bx + w + 12, y + 2), f"map {r['coverage_fraction_weighted'] * 100:.1f} % sr "
                                             f"({r['covered_cells']:,}/{r['reference_cells']:,} cells, "
                                             f"{r['coverage_fraction'] * 100:.1f} %)", size=14)
            S.text(d, (bx + w + 12, y + 22), f"effective (diagnostic) {r['effective_coverage_fraction_weighted'] * 100:.1f}"
                                             f" % sr", size=14, fill=S.INK2)
        y += rowh
    return y


def panel_f(img: Image.Image, y: int, dd: Data) -> tuple[int, dict]:
    y = NV.panel_title(img, y, "F", "Post-freeze coverage at 12 mm on the accepted Breadth-1 0.5-degree first-hit reference",
                       [SP.LABEL_REFERENCE])
    d = ImageDraw.Draw(img)
    if dd.ev is None:
        S.text(d, (60, y + 10), "evaluation not run", size=S.T_HEAD, bold=True)
        return y + 60, {}
    yy = coverage_bars(img, d, 50, y + 6, 700, dd)
    d = ImageDraw.Draw(img)
    a, e = dd.ev["aggregate"], dd.ev["effective_geometry_diagnostic"]
    bx = 1460
    d.rectangle([bx, y + 6, W - 40, y + 260], fill=S.PANEL, outline=S.FAINT, width=2)
    lines = [("PRIMARY: final PERSISTENT maps only (memory excluded)", S.INK),
             f"micro cell coverage {a['covered_cells']:,} / {a['reference_cells']:,} = "
             f"{a['micro_coverage'] * 100:.2f} %",
             f"solid-angle-weighted micro coverage {a['micro_coverage_weighted'] * 100:.2f} %",
             (SP.LABEL_EFFECTIVE_DIAG, S.INK2),
             f"effective-geometry diagnostic: {e['micro_coverage'] * 100:.2f} % cells, "
             f"{e['micro_coverage_weighted'] * 100:.2f} % sr",
             f"ids with no 0.5-degree first-hit cell: {dd.ev['no_reference_ids'] or 'none'}"]
    text_block(d, bx + 14, y + 16, lines, size=16, gap=34)
    hb = (bx, y + 280, W - 40, y + 420)
    S.dashed_rect(d, hb, S.MUTED, width=2)
    text_block(d, bx + 14, y + 290, [(SP.LABEL_NON_COMPARABLE, S.INK2),
                                     "Controller-01: 28,801 / 29,288 = 98.34 % within 12 mm",
                                     "(0.25-deg cyclopean samples, old domain, 25 objects)",
                                     "NOT numerically comparable: no better / worse claim"], size=15, gap=30, fill=S.INK2)
    S.text(d, (60, yy + 4), "solid bar: persistent-map coverage (solid-angle weighted); hatched bar: effective geometry "
                            "(map + memory), DIAGNOSTIC only", size=15, fill=S.INK2)
    return max(yy + 40, y + 440), {"micro": a["micro_coverage"], "weighted": a["micro_coverage_weighted"]}


def overview(dd: Data) -> tuple[Image.Image, dict]:
    img = Image.new("RGB", (W, 4300), S.SURFACE)
    oc = dd.outcome()
    y = NV.header(img, "North Star-1e - Full Coherent Multi-Entity Loop with Cross-Target Measurement Memory",
                  [f"NS1e REVIEW PENDING - Control Outcome {oc.get('outcome')} ({oc.get('scope')}); "
                   f"{len(dd.steps)} new physical actions from the accepted NS1d state",
                   "accepted Controller-02 (ns1c2_phase.SceneMachine) - M2 effective geometry = persistent map + memory - "
                   "fixed recentered policy charts - PERFECT correspondence - spherical H0 - target-only fusion",
                   f"{SP.LABEL_FIXED_HEAD} - {SP.LABEL_NO_NAME} - {SP.LABEL_AMBIGUOUS}: 10 / 110 / 178"],
                  BADGES["overview.png"])
    y = panel_a(img, y + 6, dd)
    y, counts = panel_b(img, y + 6, dd)
    y, growth = panel_c(img, y + 6, dd)
    y, nre = panel_d(img, y + 6, dd)
    y, term = panel_e(img, y + 6, dd)
    y, cov = panel_f(img, y + 6, dd)
    img = img.crop((0, 0, W, y + 30))
    return img, {"panels": ["A", "B", "C", "D", "E", "F"], "actions": counts, "natural_reactivations": nre,
                 "terminal": term, "coverage": cov, "memory_drawn_as": "bars of measured samples, never fused geometry",
                 "historical_shown_as": SP.LABEL_NON_COMPARABLE}


# ------------------------------------------------------------------ supporting figures
def full_timeline(dd: Data) -> tuple[Image.Image, dict]:
    img = Image.new("RGB", (W, 1500), S.SURFACE)
    y = NV.header(img, "Controller full timeline (every new action, phase, switch and event)",
                  ["one column per global step; glyph = action source; letters = machine events; vertical rule = terminal",
                   "lower strip: target map surfels after each action and the new surfels it fused"],
                  BADGES["controller-full-timeline.png"])
    d = ImageDraw.Draw(img)
    counts = timeline_grid(img, d, (40, y, W - 40, y + 760), dd, compact=False)
    legend_row(d, 50, y + 770)
    sb = (40, y + 820, W - 40, y + 1180)
    d.rectangle(sb, fill=S.PANEL, outline=S.FAINT, width=2)
    if dd.steps:
        k_last = dd.steps[-1] + (1 if dd.terminal is not None else 0)
        nst = max(1, k_last - dd.k0 + 1)
        cw = (sb[2] - sb[0] - 120) / nst
        vmax = max(max(dd.fus[k]["map_after"] for k in dd.steps), 1)
        nmax = max(max(dd.fus[k]["new"] for k in dd.steps), 1)
        for k in dd.steps:
            x = sb[0] + 120 + (k - dd.k0) * cw
            col, _g = ent_style(int(dd.dec[k]["action"]["target"]), dd.ids)
            hgt = (sb[3] - sb[1] - 60) * math.log10(1 + dd.fus[k]["map_after"]) / math.log10(1 + vmax)
            d.rectangle([x + 1, sb[3] - 10 - hgt, x + max(2, cw - 1), sb[3] - 10], fill=col)
            if dd.fus[k]["new"] == 0:
                S.xmark(d, x + cw / 2, sb[3] - 20, r=4, color=S.INK, width=2)
        S.text(d, (sb[0] + 10, sb[1] + 8), f"target map after each action (log scale, max {vmax:,}); x = zero new "
                                           f"surfels (largest single fusion +{nmax:,})", size=15)
    rows = [f"step {k}: {dd.dec[k]['action']['target']} {dd.dec[k]['scheduler_reason']} "
            f"{dd.dec[k]['action']['source'][:9]} {fmt(dd.dec[k]['action']['local_gaze_deg'])} +{dd.fus[k]['new']:,}"
            for k in dd.steps]
    S.text(d, (40, y + 1196), f"{len(rows)} actions; first: {rows[0] if rows else '-'}; last: {rows[-1] if rows else '-'}",
           size=15, fill=S.INK2)
    return img.crop((0, 0, W, y + 1240)), {"actions": counts, "steps": len(dd.steps)}


def final_geometry(dd: Data) -> tuple[Image.Image, dict]:
    img = Image.new("RGB", (W, 1520), S.SURFACE)
    y = NV.header(img, "Final persistent maps of the ten coherent entities (canonical H0; target-only fusion)",
                  ["left: equirectangular H0 view (faded = initial NS1c2 map points); right: top view x / z in metres",
                   "memory samples are NOT drawn here (they are not fused geometry)"],
                  BADGES["multi-entity-final-geometry.png"])
    groups = clusters(dd, dd.final["entities"])
    gw = 1400 // max(1, len(groups))
    for n_, gr in enumerate(groups):
        box = (40 + n_ * gw, y, 40 + (n_ + 1) * gw - 10, y + 760)
        inner, yr, pr, c = zoom_frame(img, box, f"H0 zoom {n_ + 1}", gr)
        d = ImageDraw.Draw(img)
        zoom_points(d, inner, yr, pr, c, dd, dd.initial["entities"], gr["ids"], faded=True, labels=False)
        zoom_points(d, inner, yr, pr, c, dd, dd.final["entities"], gr["ids"], nmax=6000)
    d = ImageDraw.Draw(img)
    tb = (1480, y, W - 40, y + 760)
    d.rectangle(tb, fill=S.PANEL, outline=S.FAINT, width=2)
    S.text(d, (tb[0] + 12, tb[1] + 8), "top view (x right, -z forward), metres", size=S.T_BODY, bold=True)
    allp = np.vstack([dd.map_xyz(dd.final["entities"][str(i)]) for i in dd.ids] + [np.zeros((1, 3))])
    allp = allp[np.isfinite(allp).all(axis=1)]
    lo = np.percentile(allp[:, [0, 2]], 0.5, axis=0) - 0.3
    hi = np.percentile(allp[:, [0, 2]], 99.5, axis=0) + 0.3
    lo, hi = np.minimum(lo, -0.3), np.maximum(hi, 0.3)
    inner2 = (tb[0] + 20, tb[1] + 50, tb[2] - 20, tb[3] - 40)
    sc = min((inner2[2] - inner2[0]) / (hi[0] - lo[0]), (inner2[3] - inner2[1]) / (hi[1] - lo[1]))
    mid = (lo + hi) / 2
    cx = (inner2[0] + inner2[2]) / 2 - mid[0] * sc
    cy = (inner2[1] + inner2[3]) / 2 - mid[1] * sc
    S.text(d, (tb[0] + 12, tb[3] - 30), "1 m = " + f"{sc:.0f} px; zoom groups: " + "; ".join(
        f"{n_ + 1}: {', '.join(str(i) for i in gr['ids'])}" for n_, gr in enumerate(groups)), size=14, fill=S.INK2)
    for i in dd.ids:
        xyz = dd.map_xyz(dd.final["entities"][str(i)])
        if not len(xyz):
            continue
        q = xyz[sub(len(xyz), 4000)]
        col, _g = ent_style(i, dd.ids)
        dots(d, cx + q[:, 0] * sc, cy + q[:, 2] * sc, col, r=1, box=inner2)
    NV.glyph(d, cx, cy, "diamond", S.INK, r=8)
    S.text(d, (cx + 10, cy + 6), "head (fixed)", size=14, bold=True)
    yy = y + 790
    d = ImageDraw.Draw(img)
    for n, i in enumerate(dd.ids):
        col, g = ent_style(i, dd.ids)
        a, b = dd.initial["entities"][str(i)], dd.final["entities"][str(i)]
        x = 50 + (n % 5) * 470
        yr = yy + (n // 5) * 40
        NV.glyph(d, x + 8, yr + 12, g, col, r=8)
        S.text(d, (x + 24, yr), f"{i}: {a['map']['surfels']:,} -> {b['map']['surfels']:,} surfels "
                                f"({b['own_looks']} looks)", size=16)
    return img.crop((0, 0, W, yy + 100)), {"entities": len(dd.ids), "memory_drawn": False}


def memory_flow(dd: Data) -> tuple[Image.Image, dict]:
    img = Image.new("RGB", (W, 1300), S.SURFACE)
    y = NV.header(img, "Memory flow: every new memory event (all-instance; source active target recorded)",
                  ["per event: own target samples (vermilion), coherent cross-target samples (blue), non-scheduler ids "
                   "(gray; " + SP.LABEL_AMBIGUOUS + " hatched)", "memory events 0-8 = accepted NS1d; event e = NS1e "
                                                                  "global step e - 1"],
                  BADGES["memory-flow-timeline.png"])
    d = ImageDraw.Draw(img)
    box = (40, y, W - 40, y + 560)
    d.rectangle(box, fill=S.PANEL, outline=S.FAINT, width=2)
    tot = {"own": 0, "cross": 0, "non": 0, "ambiguous": 0}
    if dd.steps:
        n = len(dd.steps)
        cw = (box[2] - box[0] - 100) / n
        vmax = max(sum(dd.mem[k]["row"]["additions"].values()) for k in dd.steps) or 1
        hmax = box[3] - box[1] - 70
        for m, k in enumerate(dd.steps):
            ev = dd.mem[k]
            own = ev["own_target_additions"]
            cross = sum(ev["coherent_cross_target_additions"].values())
            amb = sum(v for kk, v in ev["non_scheduler_additions"].items() if int(kk) in SP.EXPECTED_AMBIGUOUS)
            non = sum(ev["non_scheduler_additions"].values()) - amb
            tot["own"] += own
            tot["cross"] += cross
            tot["non"] += non
            tot["ambiguous"] += amb
            x = box[0] + 90 + m * cw
            ybase = box[3] - 30
            for val, col, hatch in ((own, S.OI_VERM, False), (cross, S.OI_BLUE, False), (non, (170, 170, 170), False),
                                    (amb, AMBIG_COL, True)):
                hgt = hmax * val / vmax
                if hgt <= 0:
                    continue
                d.rectangle([x, ybase - hgt, x + max(1, cw - 1), ybase], fill=col)
                if hatch and cw > 3:
                    S.hatch(img, (int(x), int(ybase - hgt), int(x + cw - 1), int(ybase)), (120, 120, 120), spacing=5,
                            width=1)
                    d = ImageDraw.Draw(img)
                ybase -= hgt
        S.text(d, (box[0] + 10, box[1] + 8), f"samples per memory event (max {vmax:,}); events "
                                             f"{dd.mem[dd.steps[0]]['memory_event']}..{dd.mem[dd.steps[-1]]['memory_event']}",
               size=15)
    fin = dd.final["memory"]["summary"]
    lines = [(f"NS1e memory additions: own {tot['own']:,}; coherent cross-target {tot['cross']:,}; non-scheduler "
              f"{tot['non']:,}; ambiguous ids {tot['ambiguous']:,}", S.INK),
             f"final memory: {fin['total_points']:,} samples in {len(fin['instance_ids'])} observed ids "
             f"({len(dd.final['memory']['events'])} memory events)",
             "per coherent id (own / cross): " + "; ".join(
                 f"{i}: {fin['by_id'].get(str(i), {}).get('own_target_points', 0):,} / "
                 f"{fin['by_id'].get(str(i), {}).get('cross_target_points', 0):,}" for i in dd.ids)]
    text_block(d, 50, y + 580, lines, size=16, gap=30)
    return img.crop((0, 0, W, y + 700)), {"totals": tot}


def coverage_fig(dd: Data) -> tuple[Image.Image, dict]:
    img = Image.new("RGB", (W, 2000), S.SURFACE)
    y = NV.header(img, "Coverage by entity at 12 mm (post-control; accepted Breadth-1 0.5-degree whole-sphere reference)",
                  ["green = reference cell covered by the final PERSISTENT map; vermilion x = not covered; "
                   "effective geometry is a separate DIAGNOSTIC", SP.LABEL_NON_COMPARABLE + ": Controller-01 98.34 %"],
                  BADGES["coverage-by-entity.png"])
    d = ImageDraw.Draw(img)
    if dd.ev is None:
        S.text(d, (60, y + 10), "evaluation not run", size=S.T_HEAD, bold=True)
        return img.crop((0, 0, W, y + 80)), {}
    cov = npz(dd.run / "evaluation/coverage.npz")
    tile, gap = 440, 20
    for n, i in enumerate(dd.ids):
        x = 40 + (n % 5) * (tile + gap)
        yy = y + (n // 5) * (tile + 90)
        d.rectangle([x, yy, x + tile, yy + tile], fill=S.PANEL, outline=S.FAINT, width=2)
        r = dd.ev["per_entity"][str(i)]
        S.text(d, (x + 8, yy + 6), f"{i}", size=S.T_BODY, bold=True)
        if r["status"] == SP.NO_REFERENCE or f"e{i:05d}_cells" not in cov:
            S.text(d, (x + 8, yy + 50), SP.NO_REFERENCE, size=15, bold=True, fill=S.INK2)
            continue
        cells = cov[f"e{i:05d}_cells"]
        c = cov[f"e{i:05d}_covered"]
        rr, cc = cells[:, 0], cells[:, 1]
        r0, r1, c0, c1 = rr.min(), rr.max(), cc.min(), cc.max()
        span = max(r1 - r0 + 1, c1 - c0 + 1, 8)
        sc = (tile - 50) / span
        for a, b, ok in zip(rr, cc, c):
            px, py = x + 20 + (b - c0) * sc, yy + 40 + (a - r0) * sc
            if ok:
                d.rectangle([px, py, px + max(1, sc - 1), py + max(1, sc - 1)], fill=S.OI_GREEN)
            else:
                S.xmark(d, px + sc / 2, py + sc / 2, r=max(1.5, sc / 2.5), color=S.OI_VERM, width=1)
        st = dd.statuses()[str(i)]
        S.text(d, (x + 8, yy + tile + 4), f"map {r['covered_cells']:,}/{r['reference_cells']:,} = "
                                          f"{r['coverage_fraction'] * 100:.1f} % cells, "
                                          f"{r['coverage_fraction_weighted'] * 100:.1f} % sr", size=14)
        S.text(d, (x + 8, yy + tile + 24), f"effective (diagnostic) {r['effective_coverage_fraction'] * 100:.1f} % cells; "
                                           f"{r['final_persistent_surfels']:,} surfels; {r['own_looks']} looks", size=13,
               fill=S.INK2)
        S.text(d, (x + 8, yy + tile + 44), f"terminal: {st['local']}/{st['disposition']}"
                                           + (f" ({st['reason']})" if st["reason"] else ""), size=13, fill=S.INK2)
    return img.crop((0, 0, W, y + 2 * (tile + 90) + 20)), {"entities": len(dd.ids)}


def rank1_fig(dd: Data) -> tuple[Image.Image, dict]:
    img = Image.new("RGB", (W, 1400), S.SURFACE)
    y = NV.header(img, "Rank-1 representation seam: spherical target measurements vs planar controller-state support",
                  ["valid North-Star spherical maps but zero target support in the inherited planar controller "
                   "initialization state (observed, NOT fixed)",
                   "per own look: blue bar = spherical target points (PERFECT, fused); slate bar = planar controller-state "
                   "target support"], BADGES["rank1-diagnostic.png"])
    d = ImageDraw.Draw(img)
    out = {}
    yy = y
    for i in SP.RANK1:
        looks = [dd.upd[k]["rank1_look"] for k in dd.steps if (dd.upd[k].get("rank1_look") or {}).get("target") == i]
        first = next((dd.dec[k].get("rank1_first_selection") for k in dd.steps
                      if (dd.dec[k].get("rank1_first_selection") or {}).get("target") == i), None)
        st = dd.statuses()[str(i)]
        col, g = ent_style(i, dd.ids)
        NV.glyph(d, 60, yy + 16, g, col, r=9)
        S.text(d, (80, yy + 2), f"{i}: initial planar support {dd.initial['entities'][str(i)].get('planar_support_last_look')}"
                                f"; first selected: " + ("never" if first is None else
                                                         f"{first['source']} {fmt(first['local_gaze_deg'])}, M2 effective "
                                                         f"{first['m2_effective_points']:,}") +
               f"; terminal {st['local']}/{st['disposition']} {st['reason'] or ''}", size=16, bold=True)
        vmax = max([lk["north_star_spherical_target_points"] for lk in looks]
                   + [lk["controller_state_target_support"] for lk in looks] + [1])
        for m, lk in enumerate(looks[:40]):
            x = 90 + m * 55
            h1 = 90 * lk["north_star_spherical_target_points"] / vmax
            h2 = 90 * lk["controller_state_target_support"] / vmax
            d.rectangle([x, yy + 130 - h1, x + 20, yy + 130], fill=S.OI_BLUE)
            d.rectangle([x + 24, yy + 130 - h2, x + 44, yy + 130], fill=S.SLATE, outline=S.INK2)
            NV.glyph(d, x + 22, yy + 146, SOURCE_GLYPH.get(lk["source"], "square"), S.INK, r=5,
                     hollow=lk["source"] == "cyclopean_epistemic")
        S.text(d, (90 + max(1, len(looks[:40])) * 55 + 20, yy + 60),
               f"{len(looks)} own NS1e looks; spherical total {sum(lk['north_star_spherical_target_points'] for lk in looks):,}"
               f"; planar total {sum(lk['controller_state_target_support'] for lk in looks):,}", size=15)
        out[str(i)] = {"looks": len(looks), "first": first is not None}
        yy += 200
    return img.crop((0, 0, W, yy + 20)), {"entities": out}


def reactivation_fig(dd: Data) -> tuple[Image.Image, dict]:
    reacts = [r for k in dd.steps for r in (dd.upd[k].get("natural_reactivations") or [])]
    img = Image.new("RGB", (W, 260 + 70 * len(reacts)), S.SURFACE)
    y = NV.header(img, "Natural reactivations through M2 memory (no reactivation call anywhere)",
                  ["a QUIET entity whose measured points changed (cross-target evidence) was re-probed and became "
                   "ACTIONABLE"], BADGES["natural-reactivation.png"])
    d = ImageDraw.Draw(img)
    for n, r in enumerate(reacts):
        pb, pa = r["probe_before"], r["probe_after"]
        S.text(d, (60, y + n * 70), f"{r['object']}: QUIET since {r.get('quiet_since_step')} -> step {r['global_step']} "
                                    f"(target {r['triggering_target']}, memory event {r['memory_event']}): +"
                                    f"{r['cross_target_points_added']:,} cross-target samples; revision "
                                    f"{r['revision_before']} -> {r['revision_after']}", size=S.T_SMALL, bold=True)
        S.text(d, (60, y + n * 70 + 30), f"FSG6f {(pb.get('fsg6f') or {}).get('reason')} -> "
                                         f"{(pa.get('fsg6f') or {}).get('reason')}; Cyclopean "
                                         f"{(pb.get('cyclopean') or {}).get('reason')} / eligible "
                                         f"{(pb.get('cyclopean') or {}).get('eligible_cells')} -> "
                                         f"{(pa.get('cyclopean') or {}).get('reason')} / eligible "
                                         f"{(pa.get('cyclopean') or {}).get('eligible_cells')}; next "
                                         f"{fmt((r.get('next_proposal') or {}).get('local_gaze_deg'))}", size=16)
    return img, {"reactivations": len(reacts)}


def residue_fig(dd: Data) -> tuple[Image.Image, dict]:
    rows = []
    for k in dd.steps:
        rows += [(k, g) for g in dd.dec[k].get("residue_gate_records") or []]
    if dd.terminal is not None:
        rows += [(int(dd.terminal["global_step"]), g) for g in dd.terminal.get("residue_gate_records") or []]
    rds = (dd.terminal or {}).get("machine_after_decide", dd.final["machine"])["residue_decisions"]
    img = Image.new("RGB", (W, 360 + 64 * (len(rds) + len(rows))), S.SURFACE)
    y = NV.header(img, "RESIDUE phase: one decision per DEFERRED entity (ascending id); the gate only here",
                  ["QUIET deferred -> FINALIZED without a gate call; ACTIONABLE deferred -> its UNCHANGED proposal to "
                   "final_look_gate_v1 (M2 geometry in C_i; real fixed-head H0 sensor)"], BADGES["residue-phase.png"])
    d = ImageDraw.Draw(img)
    for n, r in enumerate(rds):
        prop = r.get("proposal") or {}
        S.text(d, (60, y + n * 64), f"{r['object']} at step {r['global_step']}: {r['local_state']} -> {r['outcome']}"
                                    + (f"; proposal {prop.get('source')} {fmt(prop.get('gaze_deg'))}; gate "
                                       f"{r.get('admissible')} ({r.get('reason')})" if prop else "")
                                    + (f"; after the final look {r.get('local_state_after')}"
                                       if r.get("local_state_after") else ""), size=S.T_SMALL)
    return img.crop((0, 0, W, y + 64 * max(1, len(rds)) + 20)), {"residue_decisions": len(rds),
                                                                  "gate_records": len(rows)}


# ------------------------------------------------------------------ PLY exports
def plys(dd: Data) -> dict:
    groups, eff = [], []
    led = dd.ledger()
    for i in dd.ids:
        rec = dd.final["entities"][str(i)]
        xyz, rgb = dd.map_xyz(rec), dd.map_rgb(rec)
        ok = np.isfinite(xyz).all(axis=1)
        groups.append((i, xyz[ok], rgb[ok]))
        mem = led.snapshot(i).xyz_h
        eff.append((i, np.vstack([xyz[ok], mem]) if len(mem) else xyz[ok], None))
    return {SP.PLY_PERSISTENT: CORE.ply_bytes(groups, "North Star-1e final PERSISTENT SURFACE MAPS of the ten coherent "
                                                      "entities only (target-only fusion; canonical H0, metres)\n"
                                                      "no measurement-memory sample is included\nvertex entity_id = "
                                                      "temporary entity id (oracle segmentation aid; no names)"),
            SP.PLY_EFFECTIVE: CORE.ply_bytes(eff, f"North Star-1e {SP.LABEL_EFFECTIVE_DIAG}\npersistent map + "
                                                  "measurement memory per entity (memory samples are NOT fused)\n"
                                                  "vertex entity_id = temporary entity id")}


def render_all(run: Path) -> tuple[dict, Data]:
    dd = Data(run)
    figs = {"overview.png": overview(dd), "controller-full-timeline.png": full_timeline(dd),
            "multi-entity-final-geometry.png": final_geometry(dd), "memory-flow-timeline.png": memory_flow(dd),
            "coverage-by-entity.png": coverage_fig(dd), "rank1-diagnostic.png": rank1_fig(dd)}
    if any(dd.upd[k].get("natural_reactivations") for k in dd.steps):
        figs["natural-reactivation.png"] = reactivation_fig(dd)
    phases = (dd.terminal or {}).get("machine_after_decide", dd.final["machine"])["phases"]
    if any(p["phase"] == "RESIDUE" for p in phases):
        figs["residue-phase.png"] = residue_fig(dd)
    return figs, dd


def visualize(run: Path, vis: Path) -> dict:
    vis = Path(vis)
    vis.mkdir(parents=True, exist_ok=True)
    figs, dd = render_all(run)
    man = {"schema": "NS1e-visuals-v1", "visual_language": "Visual Language 1", "run": str(run),
           "font_hashes": S.font_hashes(), "figures": {}, "plys": {},
           "not_applicable": {k: v for k, v in {
               "natural-reactivation.png": None if "natural-reactivation.png" in figs else
               "no natural reactivation occurred", "residue-phase.png": None if "residue-phase.png" in figs else
               "RESIDUE was not entered"}.items() if v},
           "fixed_head_statement": SP.LABEL_FIXED_HEAD, "outcome": dd.outcome(),
           "memory_vs_map": "memory samples are counted and exported separately, never drawn or exported as fused "
                            "persistent geometry", "historical": SP.LABEL_NON_COMPARABLE}
    for name, (im, meta) in figs.items():
        path = vis / name
        im.save(path, format="PNG", optimize=False)
        man["figures"][name] = {"sha256": sha256(path), "size": list(im.size), "badges": BADGES[name],
                                "labels": LABELS[name], **CORE.jsonable(meta)}
    for name, b in plys(dd).items():
        (vis / name).write_bytes(b)
        r = CORE.ply_read(b)
        man["plys"][name] = {"sha256": sha256(vis / name), "vertices": int(len(r["xyz"])),
                             "entities": sorted({int(e) for e in r["entity_id"]}), "comments": r["comments"]}
    (vis / "visuals-manifest.json").write_text(json.dumps(man, indent=1, sort_keys=True) + "\n")
    return man
