"""North Star-1d: the scientific visuals (Visual Language 1; deterministic PNGs).

Contract: docs/north-star/ns1d-cross-target-measurement-memory-contract.md, section 22.

- ``overview.png``: A the accepted historical mechanism (ACCEPTED HISTORICAL REFERENCE); B one real North-Star memory
  patch (active target, every positive observed id, additions by id); C map vs memory for one observed entity (memory
  samples are NOT fused surfels); D the causal replay timeline; E the first divergence, or NO ACTION DIVERGENCE THROUGH
  STEP 7 with the memory-enriched final scene.
- ``memory-causal-timeline.png``: every observed id x memory event (own / cross / non-scheduler), revisions, decisions.
- ``effective-geometry-before-after.png``: per entity with memory, in its policy chart: map (M0) | memory samples by
  source active target | effective geometry (M2), with the M0 and M2 proposals.
- ``decision-divergence.png`` (only if a divergence occurred) and ``reactivation.png`` (only if a natural reactivation
  occurred).

Only the NS1d run, the accepted NS1c2 charts and the NS1c2 / NS1a / NS1b maps named by the replayed entity records are
read; no catalog, no name, no reference observation.
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
import ns1b_chart as CH  # noqa: E402
import ns1b_visuals as BV  # noqa: E402  (accepted NS1b drawing helpers; its Data class is never used)
import ns1c2_core as C2  # noqa: E402
import ns1d_spec as SP  # noqa: E402
import style as S  # noqa: E402  (Visual Language 1, read-only)

ORA, DER = SP.TRUTH_ORACLE, SP.TRUTH_DERIVED
W = NV.W
COMMON = [SP.LABEL_NO_RENDER, SP.LABEL_FIXED_HEAD, SP.LABEL_MEMORY, SP.LABEL_MAP, SP.LABEL_NO_NAME]
BADGES = {"overview.png": [ORA, DER], "memory-causal-timeline.png": [DER], "effective-geometry-before-after.png":
          [ORA, DER], "decision-divergence.png": [DER], "reactivation.png": [DER]}
LABELS = {"overview.png": [SP.LABEL_HISTORICAL, SP.LABEL_EFFECTIVE, SP.LABEL_ORACLE_CORR, SP.LABEL_GEOMETRY,
                           SP.LABEL_SEGMENTATION, SP.LABEL_AMBIGUOUS, SP.LABEL_BOOTSTRAP, SP.LABEL_SCHEDULER,
                           SP.LABEL_NOT_EXECUTED, SP.LABEL_M0, SP.LABEL_M1, SP.LABEL_M2] + COMMON,
          "memory-causal-timeline.png": [SP.LABEL_AMBIGUOUS, SP.LABEL_SCHEDULER, SP.LABEL_M0, SP.LABEL_M1,
                                         SP.LABEL_M2, SP.LABEL_MEMORY],
          "effective-geometry-before-after.png": [SP.LABEL_EFFECTIVE, SP.LABEL_MAP, SP.LABEL_MEMORY, SP.LABEL_H0,
                                                  SP.LABEL_M0, SP.LABEL_M2],
          "decision-divergence.png": [SP.LABEL_M0, SP.LABEL_M1, SP.LABEL_M2, SP.LABEL_NOT_EXECUTED],
          "reactivation.png": [SP.LABEL_MEMORY, SP.LABEL_M2]}
TARGET_COL = S.OI_VERM
CROSS_COLS = [S.OI_BLUE, S.OI_GREEN, S.OI_PURPLE, S.OI_ORANGE, S.WINE, S.OI_SKY]
OTHER_COLS = [(170, 150, 110), (150, 170, 140), (160, 140, 170), (120, 150, 170), (175, 135, 120), (140, 140, 140)]
AMBIG_COL = (196, 192, 184)
MAP_COL = S.GEOM_FAR
SOURCE_GLYPH = {172: ("circle", S.OI_VERM), 202: ("diamond", S.OI_PURPLE)}

j, npz, sub, dots, text_block = BV.j, BV.npz, BV.sub, BV.dots, BV.text_block


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fmt(v, nd=1) -> str:
    return "-" if v is None else f"({v[0]:+.{nd}f}, {v[1]:+.{nd}f})"


def step_label(e: int) -> str:
    return "NS1b action" if e == 0 else f"NS1c2 step {e - 1}"


class Data:
    def __init__(self, run: Path) -> None:
        self.run = Path(run)
        self.rp = j(self.run / "replay/replay.json")
        self.el = j(self.run / "events/event-list.json")
        self.ka = j(self.run / "known-answer/known-answer.json")
        self.consumed = list(self.rp["consumed_events"])
        self.last = max(self.consumed)
        self.states = {e: j(self.run / SP.state_rel(e)) for e in self.consumed}
        self.events = {e: j(self.run / f"{SP.event_rel(e)}/event.json") for e in self.consumed}
        self.decisions = {int(k): j(self.run / f"replay/decisions/before-step-{int(k):02d}.json")
                          for k in self.rp["decisions"]}
        self.div = j(self.run / "replay/divergence.json") if self.rp["divergence"] else None
        self.final = None if self.rp["divergence"] else j(self.run / "replay/final.json")
        self.charts = j(SP.NS1C2_RUN / "charts/policy-charts.json")["charts"]
        self._patch = {}

    def patch(self, e: int) -> dict:
        if e not in self._patch:
            self._patch[e] = npz(self.run / f"{SP.event_rel(e)}/memory-patch.npz")
        return self._patch[e]

    def target(self, e: int) -> int:
        return int(self.events[e]["active_target"])

    def rows(self, e: int, mode: str) -> dict:
        return {int(r["temporary_entity_id"]): r for r in self.states[e]["tables"][mode]}

    def map_xyz(self, e: int, i: int) -> np.ndarray:
        rec = self.states[e]["contexts"][str(i)]
        return np.asarray(npz(C2.resolve(rec["map"]["path"], SP.NS1C2_RUN))["xyz_h"], np.float64)

    def memory(self, upto: int, i: int) -> list[tuple[int, int, np.ndarray]]:
        """(event, active target, samples) of observed id i, events 0..upto, from the saved memory patches."""
        out = []
        for e in self.consumed:
            if e > upto:
                break
            p = self.patch(e)
            m = p["valid"] & (p["instance_id"] == int(i))
            if m.any():
                out.append((e, self.target(e), np.asarray(p["xyz_h"][m], np.float64)))
        return out

    def first_cross_event(self) -> int:
        for e in self.consumed:
            if self.events[e]["coherent_cross_target_additions"]:
                return e
        return 0

    def best_entity(self) -> int:
        last = self.rows(self.last, "M2")
        cross = {i: r["cross_memory_points"] for i, r in last.items()}
        best = max(sorted(cross), key=lambda i: cross[i])
        return best if cross[best] > 0 else SP.CONTINUING

    def memory_entities(self) -> list[int]:
        last = self.rows(self.last, "M2")
        return [i for i in sorted(last) if last[i]["memory_points"] > 0]

    def outcome(self) -> str:
        return self.rp["outcome_reading"]


def chart_angles(xyz_h0: np.ndarray, r_hc) -> tuple[np.ndarray, np.ndarray]:
    c = CH.to_chart(np.asarray(xyz_h0, np.float64), np.asarray(r_hc, np.float64))
    yaw = np.degrees(np.arctan2(c[:, 0], -c[:, 2]))
    pitch = np.degrees(np.arctan2(c[:, 1], np.hypot(c[:, 0], c[:, 2])))
    return yaw, pitch


DOMAIN = (-25.0, 25.0, -20.0, 20.0)       # the FSG6f / Cyclopean local chart domain (yaw, pitch; degrees)


def extent_of(pairs, box, pad: float = 1.5) -> tuple:
    """A data extent (yaw0, yaw1, pitch0, pitch1) inside the chart domain, padded, with the box's aspect ratio."""
    ys = np.concatenate([np.asarray(a, float) for a, _b in pairs if len(np.atleast_1d(a))] or [np.zeros(1)])
    ps = np.concatenate([np.asarray(b, float) for _a, b in pairs if len(np.atleast_1d(b))] or [np.zeros(1)])
    ok = (ys >= DOMAIN[0]) & (ys <= DOMAIN[1]) & (ps >= DOMAIN[2]) & (ps <= DOMAIN[3])
    ys, ps = (ys[ok], ps[ok]) if ok.any() else (np.zeros(1), np.zeros(1))
    y0, y1, p0, p1 = ys.min() - pad, ys.max() + pad, ps.min() - pad, ps.max() + pad
    w, h = box[2] - box[0] - 24, box[3] - box[1] - 50
    span = max((y1 - y0) / w, (p1 - p0) / h)
    cy, cp = (y0 + y1) / 2, (p0 + p1) / 2
    return (cy - span * w / 2, cy + span * w / 2, cp - span * h / 2, cp + span * h / 2)


def chart_box(d, box, title: str, ext: tuple = DOMAIN, tag: str = "POLICY CHART C_i") -> tuple:
    d.rectangle(box, fill=S.PANEL, outline=S.FAINT, width=2)
    S.text(d, (box[0] + 10, box[1] + 6), title, size=S.T_SMALL, bold=True)
    inner = (box[0] + 12, box[1] + 38, box[2] - 12, box[3] - 12)
    step = 1.0 if ext[1] - ext[0] < 12 else 5.0
    for yy in np.arange(math.ceil(ext[0] / step) * step, ext[1] + 1e-9, step):
        a = inner[0] + (yy - ext[0]) / (ext[1] - ext[0]) * (inner[2] - inner[0])
        d.line([a, inner[1], a, inner[3]], fill=S.GRID, width=1)
    for pp in np.arange(math.ceil(ext[2] / step) * step, ext[3] + 1e-9, step):
        b = inner[1] + (ext[3] - pp) / (ext[3] - ext[2]) * (inner[3] - inner[1])
        d.line([inner[0], b, inner[2], b], fill=S.GRID, width=1)
    f = S.font(13, True)
    d.text((inner[2] - d.textlength(tag, font=f) - 4, inner[3] - 18), tag, font=f, fill=S.MUTED)
    lab = f"yaw {ext[0]:+.1f}..{ext[1]:+.1f}, pitch {ext[2]:+.1f}..{ext[3]:+.1f} deg (grid {step:g} deg)"
    S.text(d, (inner[0] + 4, inner[1] + 2), lab, size=13, fill=S.INK2)
    chart_box.ext = ext
    return inner


def to_box(yaw, pitch, inner, ext: tuple | None = None):
    ext = ext or getattr(chart_box, "ext", DOMAIN)
    u = inner[0] + (np.asarray(yaw) - ext[0]) / (ext[1] - ext[0]) * (inner[2] - inner[0])
    v = inner[1] + (ext[3] - np.asarray(pitch)) / (ext[3] - ext[2]) * (inner[3] - inner[1])
    return u, v


def proposal_marks(d, inner, m0, m2, ext) -> None:
    if m0 is not None:
        x, y = to_box(m0[0], m0[1], inner, ext)
        NV.glyph(d, float(x), float(y), "square", S.INK, r=10, hollow=True)
    if m2 is not None:
        x, y = to_box(m2[0], m2[1], inner, ext)
        S.crosshair(d, float(x), float(y), r=13, solid=False, color=S.OI_VERM)


def sources_text(mem) -> str:
    by = {}
    for e, tgt, _x in mem:
        by.setdefault(int(tgt), []).append(int(e))
    return "; ".join(f"target {tg} @ E{','.join(str(v) for v in es)}" for tg, es in sorted(by.items()))


def chart_triplet(d, boxes, titles, mp, mem, r, m0, m2, nmap: int = 4000) -> tuple:
    """Map | memory samples | effective geometry, sharing one data extent; returns the extent."""
    mp_a = chart_angles(mp[sub(len(mp), nmap)], r) if len(mp) else (np.zeros(0), np.zeros(0))
    mem_a = [(tgt, chart_angles(xyz[sub(len(xyz), 2000)], r)) for _e, tgt, xyz in mem]
    pairs = [mp_a] + [a for _t, a in mem_a]
    for g in (m0, m2):
        if g is not None:
            pairs.append((np.array([g[0]]), np.array([g[1]])))
    ext = extent_of(pairs, boxes[0])
    for k, b in enumerate(boxes):
        inner = chart_box(d, b, titles[k], ext)
        if k in (0, 2) and len(mp_a[0]):
            u, v = to_box(mp_a[0], mp_a[1], inner, ext)
            dots(d, u, v, MAP_COL, r=1, box=inner)
        if k in (1, 2):
            for tgt, (a, bb) in mem_a:
                g, col = SOURCE_GLYPH.get(tgt, ("square", S.OI_GREEN))
                u, v = to_box(a, bb, inner, ext)
                for xx, yy in zip(u, v):
                    if inner[0] < xx < inner[2] and inner[1] < yy < inner[3]:
                        NV.glyph(d, xx, yy, g, col, r=2, outline=col)
        if k == 0:
            proposal_marks(d, inner, m0, None, ext)
        if k == 2:
            proposal_marks(d, inner, m0, m2, ext)
    return ext


# ------------------------------------------------------------------ overview panels
def panel_a(img: Image.Image, y: int, dd: Data) -> int:
    y = NV.panel_title(img, y, "A", "Accepted historical mechanism: Controller-01 instance-keyed measurement memory",
                       [SP.LABEL_HISTORICAL])
    d = ImageDraw.Draw(img)
    x0 = 60
    boxes = [("one active observation", "target A is fixated", (x0, y + 20, x0 + 330, y + 120)),
             ("measured samples by OBSERVED id", "A (own) + B, C (cross-target)", (x0 + 420, y + 20, x0 + 820,
                                                                                    y + 120)),
             ("InstanceMeasurementMemory", "append-only; provenance kept", (x0 + 910, y + 20, x0 + 1300, y + 120))]
    for t1, t2, b in boxes:
        d.rounded_rectangle(b, radius=10, fill=S.WHITE, outline=S.INK2, width=3)
        S.text(d, (b[0] + 14, b[1] + 14), t1, size=S.T_BODY, bold=True)
        S.text(d, (b[0] + 14, b[1] + 52), t2, size=S.T_SMALL, fill=S.INK2)
    for (a, _x, b0), (_c, _y, b1) in zip(boxes, boxes[1:]):
        S.arrow(d, b0[2] + 8, (b0[1] + b0[3]) / 2, b1[0] - 8, (b1[1] + b1[3]) / 2, width=4)
    outs = [("per-id revision", "(own looks, measured points)"),
            ("per-id effective geometry", "persistent map + memory samples")]
    for n, (t1, t2) in enumerate(outs):
        b = (x0 + 1390, y + 10 + n * 66, x0 + 1830, y + 66 + n * 66)
        d.rounded_rectangle(b, radius=8, fill=S.WHITE, outline=S.OI_BLUE, width=3)
        S.text(d, (b[0] + 12, b[1] + 6), t1, size=S.T_SMALL, bold=True)
        S.text(d, (b[0] + 12, b[1] + 30), t2, size=16, fill=S.INK2)
        S.arrow(d, x0 + 1308, y + 70, b[0] - 6, (b[1] + b[3]) / 2, width=3, head=14)
    S.text(d, (x0 + 1860, y + 30), "B re-probed;", size=S.T_SMALL, bold=True)
    S.text(d, (x0 + 1860, y + 58), "QUIET -> ACTIONABLE =", size=S.T_SMALL)
    S.text(d, (x0 + 1860, y + 86), "natural reactivation", size=S.T_SMALL)
    mr, re = dd.ka["memory_rebuild"], dd.ka["reactivation_109"]
    lines = [("Accepted Controller-01 (literal pins, reproduced here from its 141 saved name-free patches):", S.INK),
             f"memory {mr['total_points']:,} points in {mr['observed_instances']} observed ids; over the "
             f"{mr['localized_objects']} localized objects own {mr['own_target_points']:,} / cross-target "
             f"{mr['cross_target_points']:,} = {mr['cross_fraction_pct']} % cross-target; per-look additions reproduced "
             f"{mr['looks'] - len(mr['addition_mismatches'])}/{mr['looks']}",
             f"2 natural reactivations. Reproduced: object 109 QUIET after step 4; 110's look at step 7 adds "
             f"{re['added_since_quiet']['points']} cross-target samples; revision {re['revision_before']} -> "
             f"{re['revision_after']} (own looks unchanged, map unchanged);",
             f"re-probe: Cyclopean eligible {re['summary_before']['cyclopean']['eligible_cells']} -> "
             f"{re['summary_after']['cyclopean']['eligible_cells']}, proposal {fmt(re['proposal_after'])}; the accepted "
             f"adapter emits natural_reactivation (trigger 110) - equal to the accepted Controller-02 event"]
    text_block(d, x0, y + 150, lines, size=S.T_SMALL, gap=30)
    return y + 290


def id_role(i: int, target: int) -> str:
    if i == target:
        return "active target (own)"
    if i in SP.COHERENT:
        return "coherent entity: CROSS-TARGET"
    if i in SP.AMBIGUOUS:
        return SP.LABEL_AMBIGUOUS
    return "positive id, not a scheduler entity"


def id_colors(ids: list[int], target: int) -> dict:
    cols, nc, no = {}, 0, 0
    for i in ids:
        if i == target:
            cols[i] = TARGET_COL
        elif i in SP.COHERENT:
            cols[i] = CROSS_COLS[nc % len(CROSS_COLS)]
            nc += 1
        elif i in SP.AMBIGUOUS:
            cols[i] = AMBIG_COL
        else:
            cols[i] = OTHER_COLS[no % len(OTHER_COLS)]
            no += 1
    return cols


def raster_image(p: dict, cols: dict, scale: int = 2) -> tuple[Image.Image, dict]:
    ids = p["instance_id"]
    rgb = np.full(ids.shape + (3,), S.UNKNOWN_BG, np.uint8)
    for i, c in cols.items():
        rgb[(ids == i) & p["valid"]] = c
    im = Image.fromarray(rgb, "RGB").resize((ids.shape[1] * scale, ids.shape[0] * scale), Image.NEAREST)
    cents = {}
    for i in cols:
        rr, cc = np.nonzero((ids == i) & p["valid"])
        if rr.size:
            cents[i] = (float(np.median(cc)) * scale, float(np.median(rr)) * scale)
    return im, cents


def panel_b(img: Image.Image, y: int, dd: Data) -> tuple[int, int]:
    e = dd.first_cross_event()
    ev = dd.events[e]
    t = int(ev["active_target"])
    y = NV.panel_title(img, y, "B", f"One real memory patch: event {e} ({step_label(e)}), target {t}",
                       [SP.LABEL_ORACLE_CORR, SP.LABEL_GEOMETRY, SP.LABEL_SEGMENTATION])
    d = ImageDraw.Draw(img)
    p = dd.patch(e)
    ids = sorted(int(k) for k in ev["additions"])
    cols = id_colors(ids, t)
    im, cents = raster_image(p, cols)
    ox, oy = 60, y + 10
    img.paste(im, (ox, oy))
    for i in ids:
        if i in SP.AMBIGUOUS:
            small = Image.fromarray(((p["instance_id"] == i) & p["valid"]).astype(np.uint8) * 255).resize(
                (512, 512), Image.NEAREST)
            mask = Image.new("L", img.size, 0)
            mask.paste(small, (ox, oy))
            S.hatch(img, (ox, oy, ox + 512, oy + 512), (150, 146, 138), spacing=10, width=2, mask=mask)
    d = ImageDraw.Draw(img)
    d.rectangle([ox - 2, oy - 2, ox + 514, oy + 514], outline=S.INK2, width=2)
    for i, (cx, cy) in cents.items():
        S.text(d, (ox + cx, oy + cy), str(i), size=S.T_BODY, bold=True, anchor="mm")
    S.text(d, (ox, oy + 522), "256 x 256 left raw core: H0 spherical samples (valid = geometry, finite, id > 0)",
           size=16, fill=S.INK2)
    x = ox + 560
    S.text(d, (x, oy), f"event {e}: {ev['source']}, active target {t}, H0 gaze {fmt(ev['world_gaze_deg'], 3)}",
           size=S.T_BODY, bold=True)
    S.text(d, (x, oy + 34), f"{ev['patch']['valid_samples']:,} valid positive-id samples appended ONCE "
                            f"(source_global_index = {e}, source_active_target_id = {t})", size=S.T_SMALL)
    yy = oy + 80
    for i in ids:
        d.rectangle([x, yy + 4, x + 26, yy + 26], fill=cols[i], outline=S.INK2, width=1)
        if i in SP.AMBIGUOUS:
            S.hatch(img, (x, yy + 4, x + 26, yy + 26), (150, 146, 138), spacing=6, width=2)
            d = ImageDraw.Draw(img)
        S.text(d, (x + 40, yy), f"id {i}: +{ev['additions'][str(i)]:,} samples -> memory[{i}]", size=S.T_SMALL,
               bold=i in SP.COHERENT)
        S.text(d, (x + 560, yy), id_role(i, t), size=S.T_SMALL, fill=S.INK2)
        yy += 40
    st = dd.states[e]
    prev = dd.states[e - 1] if e - 1 in dd.states else None
    yy += 14
    S.text(d, (x, yy), "Effect on the scheduler entities (M2 revision = own looks, measured points):", size=S.T_SMALL,
           bold=True)
    yy += 32
    r2 = {int(r["temporary_entity_id"]): r for r in st["tables"]["M2"]}
    p2 = {int(r["temporary_entity_id"]): r for r in prev["tables"]["M2"]} if prev else {}
    for i in ids:
        if i not in SP.COHERENT:
            continue
        before = p2.get(i, {}).get("revision")
        S.text(d, (x + 20, yy), f"{i}: revision {before} -> {r2[i]['revision']}; re-probed "
                                f"({'fresh' if str(i) in st['fresh_probes']['M2'] else 'cached'}); map unchanged "
                                f"{r2[i]['map_surfels']:,} surfels{'' if i == t else ' (cross-target NOT fused)'}",
               size=S.T_SMALL)
        yy += 30
    S.text(d, (x, yy + 8), "Memory != persistent map. Scheduler identity = the 10 coherent ids only.", size=S.T_SMALL,
           fill=S.INK2)
    return oy + 560, e


def panel_c(img: Image.Image, y: int, dd: Data) -> tuple[int, int]:
    i = dd.best_entity()
    e = dd.last
    y = NV.panel_title(img, y, "C", f"Map vs memory for entity {i} after memory event {e} (its policy chart C_{i})",
                       [SP.LABEL_EFFECTIVE])
    d = ImageDraw.Draw(img)
    r = np.asarray(dd.charts[str(i)]["R_HC"], np.float64)
    mp = dd.map_xyz(e, i)
    mem = dd.memory(e, i)
    w, h, gap = 700, 470, 30
    boxes = [(60 + k * (w + gap), y + 6, 60 + k * (w + gap) + w, y + 6 + h) for k in range(3)]
    row = dd.rows(e, "M2")[i]
    r0 = dd.rows(e, "M0")[i]
    n_mem = sum(len(m[2]) for m in mem)
    titles = [f"persistent SurfaceMap: {len(mp):,} surfels (unchanged)",
              f"memory samples: {n_mem:,} (NOT fused surfels)",
              f"effective geometry M2 = map + memory: {len(mp) + n_mem:,}"]
    chart_triplet(d, boxes, titles, mp, mem, r, r0["local_gaze_deg"], row["local_gaze_deg"])
    ty = y + h + 18
    S.text(d, (60, ty), "memory provenance (glyph = source active target): circle = measured while 172 was active, "
                        "diamond = while 202 was active; " + sources_text(mem), size=S.T_SMALL)
    S.text(d, (60, ty + 30), f"probe M0 (map only): {r0['fsg6f']} / {r0['cyclopean']}, eligible "
                             f"{r0['cyclopean_eligible']}, proposal {r0['source']} {fmt(r0['local_gaze_deg'])} "
                             f"(black hollow square)", size=S.T_SMALL)
    S.text(d, (60, ty + 60), f"probe M2 (map + memory): {row['fsg6f']} / {row['cyclopean']}, eligible "
                             f"{row['cyclopean_eligible']}, proposal {row['source']} {fmt(row['local_gaze_deg'])} "
                             f"(red dashed cross-hair)", size=S.T_SMALL)
    S.text(d, (60, ty + 90), f"revision M0 {r0['revision']}  ->  M2 {row['revision']} (own {row['own_memory_points']:,} "
                             f"+ cross {row['cross_memory_points']:,} measured points); map surfels "
                             f"{row['map_surfels']:,} in every mode", size=S.T_SMALL, fill=S.INK2)
    return ty + 130, i


def panel_d(img: Image.Image, y: int, dd: Data) -> int:
    y = NV.panel_title(img, y, "D", "Causal replay: memory events, revisions and decisions (M2 = architecture under test)",
                       [SP.LABEL_SCHEDULER, SP.LABEL_NO_RENDER])
    d = ImageDraw.Draw(img)
    x0, cw, rh = 330, 215, 34
    evs = list(range(len(dd.el["events"])))
    for e in evs:
        x = x0 + e * cw
        S.text(d, (x + 8, y), f"E{e}: {step_label(e)}", size=16, bold=True)
        S.text(d, (x + 8, y + 22), "target " + str(dd.el["events"][e]["target"]) +
               ("" if e in dd.consumed else "  NOT CONSUMED"), size=15, fill=S.INK2)
    yy = y + 56
    for i in SP.COHERENT:
        S.text(d, (60, yy + 6), f"entity {i}" + ("  (rank 1)" if i in SP.RANK1 else ""), size=S.T_SMALL)
        d.line([60, yy + rh, x0 + len(evs) * cw, yy + rh], fill=S.GRID, width=1)
        for e in dd.consumed:
            x = x0 + e * cw + 10
            ev = dd.events[e]
            st = dd.states[e]
            rows = {int(r["temporary_entity_id"]): r for r in st["tables"]["M2"]}
            if int(ev["active_target"]) == i:
                S.square(d, x + 8, yy + 16, r=7, color=TARGET_COL)
                S.text(d, (x + 22, yy + 4), f"own +{ev['own_target_additions']:,}", size=15)
            elif str(i) in ev["coherent_cross_target_additions"]:
                NV.glyph(d, x + 8, yy + 16, "diamond", S.OI_BLUE, r=7, hollow=True)
                S.text(d, (x + 22, yy + 4), f"cross +{ev['coherent_cross_target_additions'][str(i)]:,}", size=15,
                       bold=True)
            if str(i) in st["fresh_probes"]["M2"] and e > 0:
                S.ring(d, x + 190, yy + 16, r=7, color=S.INK, width=2)
            if rows[i]["label"] != "ACTIONABLE":
                S.text(d, (x + 132, yy + 6), rows[i]["label"], size=13, bold=True, fill=S.INK2)
        yy += rh
    S.text(d, (60, yy + 8), "next action", size=S.T_SMALL, bold=True)
    for k in sorted(dd.decisions):
        rec = dd.decisions[k]
        x = x0 + k * cw + 10
        ok = not rec["differences"]["M2"]
        x = x0 + (k + 1) * cw - 60
        txt = ("M0=M1=M2=acc." if ok and not rec["differences"]["M1"] else f"M2 {'=' if ok else '!='} accepted")
        S.text(d, (x, yy + 4), f"step {k}", size=14, bold=True)
        S.text(d, (x, yy + 24), txt, size=14, bold=not ok, fill=S.INK if ok else S.OI_VERM)
        a = rec["accepted"]
        S.text(d, (x, yy + 44), f"{a['target']} {a['decision']} {'FSG6f' if a['source'] == 'fsg6f' else 'Cyc'}",
               size=14, fill=S.INK2)
    yy += 74
    S.square(d, 70, yy + 12, r=7, color=TARGET_COL)
    S.text(d, (86, yy), "own look of the active target (map fused, memory appended)", size=15)
    NV.glyph(d, 640, yy + 12, "diamond", S.OI_BLUE, r=7, hollow=True)
    S.text(d, (656, yy), "cross-target memory only (map NOT fused, context untouched)", size=15)
    S.ring(d, 1230, yy + 12, r=7, color=S.INK, width=2)
    S.text(d, (1246, yy), "M2 revision changed -> fresh probe (cache invalidated)", size=15)
    return yy + 40


def panel_e(img: Image.Image, y: int, dd: Data) -> tuple[int, bool]:
    if dd.div is not None:
        dv = dd.div
        y = NV.panel_title(img, y, "E", f"FIRST CAUSAL DIVERGENCE before NS1c2 step {dv['before_ns1c2_step']}",
                           [SP.LABEL_NOT_EXECUTED])
        d = ImageDraw.Draw(img)
        for n, (lab, key) in enumerate(((SP.LABEL_M0, "m0_action"), (SP.LABEL_M1, "m1_action"),
                                        (SP.LABEL_M2, "m2_action"))):
            a = dv[key]
            x = 60 + n * 760
            d.rounded_rectangle([x, y + 10, x + 720, y + 170], radius=8, fill=S.WHITE,
                                outline=S.OI_VERM if key == "m2_action" else S.INK2, width=3)
            S.text(d, (x + 14, y + 20), lab, size=S.T_BODY, bold=True)
            S.text(d, (x + 14, y + 56), f"target {a.get('target')} {a.get('decision')}  source {a.get('source')}",
                   size=S.T_SMALL)
            S.text(d, (x + 14, y + 86), f"local {fmt(a.get('local_gaze_deg'))}  H0 {fmt(a.get('world_gaze_deg'), 3)}",
                   size=S.T_SMALL)
        d = ImageDraw.Draw(img)
        S.text(d, (60, y + 190), f"differences (M2 vs accepted): {dv['differences']}; {dv['attribution']['reading']}; "
                                 "the divergent action is NOT EXECUTED; no later observation consumed", size=S.T_SMALL,
               bold=True)
        return y + 240, True
    y = NV.panel_title(img, y, "E", "NO ACTION DIVERGENCE THROUGH STEP 7 - the memory-enriched final scene",
                       [SP.LABEL_NOT_EXECUTED])
    d = ImageDraw.Draw(img)
    last = dd.last
    r0, r2 = dd.rows(last, "M0"), dd.rows(last, "M2")
    cols = [60, 220, 360, 520, 700, 880, 1080, 1290, 1650]
    heads = ["entity", "own looks", "map surfels", "memory own", "memory cross", "M2 revision", "M2 state",
             "M0 proposal (map only)", "M2 proposal (full memory)"]
    for x, h in zip(cols, heads):
        S.text(d, (x, y + 4), h, size=S.T_SMALL, bold=True)
    yy = y + 36
    for i in SP.COHERENT:
        a, b = r0[i], r2[i]
        changed = (a["source"], a["local_gaze_deg"]) != (b["source"], b["local_gaze_deg"])
        vals = [str(i), str(b["own_looks"]), f"{b['map_surfels']:,}", f"{b['own_memory_points']:,}",
                f"{b['cross_memory_points']:,}", str(b["revision"]), b["label"],
                f"{a['source'] or '-'} {fmt(a['local_gaze_deg'])}", f"{b['source'] or '-'} {fmt(b['local_gaze_deg'])}"]
        for x, v in zip(cols, vals):
            S.text(d, (x, yy), v, size=16, bold=(x == cols[-1] and changed))
        if changed:
            S.text(d, (cols[-1] + 360, yy), "changed (soft)", size=15, bold=True, fill=S.OI_VERM)
        yy += 27
    nd = dd.final["next_decisions"]
    S.text(d, (60, yy + 10), "next scheduler decision after step 7 (descriptive, NOT EXECUTED): " + "; ".join(
        f"{m}: {nd[m].get('target')} {nd[m].get('decision')} {nd[m].get('source')} {fmt(nd[m].get('local_gaze_deg'))}"
        for m in SP.MODES), size=S.T_SMALL, bold=True)
    return yy + 50, False


def overview(dd: Data) -> tuple[Image.Image, dict]:
    img = Image.new("RGB", (W, 3150), S.SURFACE)
    tot = dd.rp["memory"]
    y = NV.header(img, "North Star-1d - Controller-Phase Cross-Target Measurement Memory",
                  [f"NS1d REVIEW PENDING - reading: {dd.outcome()}",
                   f"the accepted InstanceMeasurementMemory over {len(dd.consumed)} controller-phase observations "
                   f"(NS1b action + NS1c2 steps); {tot['total_points']:,} memory samples in "
                   f"{len(tot['instance_ids'])} observed ids; persistent maps target-only (unchanged)",
                   f"{SP.LABEL_NO_RENDER} - {SP.LABEL_FIXED_HEAD} - {SP.LABEL_BOOTSTRAP} - {SP.LABEL_NO_NAME}"],
                  BADGES["overview.png"])
    y = panel_a(img, y + 6, dd)
    y, ev_b = panel_b(img, y + 6, dd)
    y, ent_c = panel_c(img, y + 6, dd)
    y = panel_d(img, y + 6, dd)
    y, div = panel_e(img, y + 6, dd)
    img = img.crop((0, 0, W, y + 30))
    return img, {"panels": ["A", "B", "C", "D", "E"], "patch_event_shown": ev_b, "map_memory_entity_shown": ent_c,
                 "divergence_shown": div, "memory_drawn_as": "measured samples, glyph by source active target",
                 "source_active_target_shown": True, "events_in_timeline": len(dd.el["events"]),
                 "consumed_events": dd.consumed}


# ------------------------------------------------------------------ supporting figures
def timeline(dd: Data) -> tuple[Image.Image, dict]:
    ids = sorted({int(k) for e in dd.consumed for k in dd.events[e]["additions"]},
                 key=lambda i: (0 if i in SP.COHERENT else 1 if i in SP.AMBIGUOUS else 2, i))
    img = Image.new("RGB", (W, 200 + 40 * (len(ids) + 8)), S.SURFACE)
    y = NV.header(img, "Memory causal timeline: every observed id x memory event",
                  ["own = sample of the active target; cross = sample of another id; memory != map; scheduler = "
                   "10 coherent ids", SP.LABEL_AMBIGUOUS + " (110 is stored in memory, never scheduled)"],
                  BADGES["memory-causal-timeline.png"])
    d = ImageDraw.Draw(img)
    x0, cw, rh = 430, 200, 40
    for e in range(len(dd.el["events"])):
        S.text(d, (x0 + e * cw + 6, y), f"E{e} {step_label(e)}", size=15, bold=True)
        S.text(d, (x0 + e * cw + 6, y + 20), f"target {dd.el['events'][e]['target']}", size=15, fill=S.INK2)
    S.text(d, (x0 + 9 * cw + 10, y), "total own / cross", size=15, bold=True)
    yy = y + 50
    last = dd.states[dd.last]["memory"]["by_id"]
    for i in ids:
        role = "coherent" if i in SP.COHERENT else ("AMBIGUOUS ORACLE ID - EXCLUDED" if i in SP.AMBIGUOUS
                                                     else "not a scheduler entity")
        S.text(d, (40, yy + 8), f"id {i}", size=S.T_SMALL, bold=i in SP.COHERENT)
        S.text(d, (130, yy + 10), role, size=14, fill=S.INK2)
        if i in SP.AMBIGUOUS:
            S.hatch(img, (x0, yy + 2, x0 + 9 * cw, yy + rh - 2), (225, 222, 215), spacing=12, width=1)
            d = ImageDraw.Draw(img)
        for e in dd.consumed:
            ev = dd.events[e]
            n = ev["additions"].get(str(i))
            if not n:
                continue
            x = x0 + e * cw + 6
            own = int(ev["active_target"]) == i
            if own:
                S.square(d, x + 8, yy + 20, r=7, color=TARGET_COL)
            elif i in SP.COHERENT:
                NV.glyph(d, x + 8, yy + 20, "diamond", S.OI_BLUE, r=7, hollow=True)
            else:
                S.xmark(d, x + 8, yy + 20, r=6, color=S.MUTED, width=2)
            S.text(d, (x + 22, yy + 9), f"{'own' if own else 'cross'} +{n:,}", size=15, bold=i in SP.COHERENT)
        p = last.get(str(i), {})
        S.text(d, (x0 + 9 * cw + 10, yy + 9), f"{p.get('own_target_points', 0):,} / {p.get('cross_target_points', 0):,}",
               size=15)
        d.line([40, yy + rh, x0 + 9 * cw + 300, yy + rh], fill=S.GRID, width=1)
        yy += rh
    yy += 14
    for mode, lab in (("M0", SP.LABEL_M0), ("M1", SP.LABEL_M1), ("M2", SP.LABEL_M2)):
        S.text(d, (40, yy + 6), lab, size=15, bold=True)
        for k in sorted(dd.decisions):
            rec = dd.decisions[k]
            ok = not rec["differences"][mode]
            a = rec["actions"][mode]
            S.text(d, (x0 + k * cw + 6 + cw // 2, yy + 6), ("= accepted " if ok else "DIFFERS ") +
                   f"{a.get('target')}", size=15, bold=not ok, fill=S.INK if ok else S.OI_VERM)
        yy += 34
    S.text(d, (40, yy + 10), "decision before NS1c2 step k sits between memory events k and k+1 (memory events 0..k); "
                             "accepted = the NS1c2 trace", size=15, fill=S.INK2)
    return img.crop((0, 0, W, yy + 50)), {"ids": ids, "consumed_events": dd.consumed,
                                          "ambiguous_marked": [i for i in ids if i in SP.AMBIGUOUS]}


def before_after(dd: Data) -> tuple[Image.Image, dict]:
    ents = dd.memory_entities()
    rowh = 420
    img = Image.new("RGB", (W, 260 + rowh * len(ents)), S.SURFACE)
    y = NV.header(img, "Effective geometry before / after memory, in each entity's policy chart C_i",
                  ["left: persistent map = M0 geometry; middle: memory samples (glyph = source active target); right: "
                   "M2 effective geometry = map + memory (no dedup, no fusion)",
                   "black hollow square = M0 proposal; red dashed cross-hair = M2 proposal; " + SP.LABEL_H0 + " points shown in C_i"],
                  BADGES["effective-geometry-before-after.png"])
    d = ImageDraw.Draw(img)
    e = dd.last
    out = {}
    for n, i in enumerate(ents):
        yy = y + n * rowh
        r = np.asarray(dd.charts[str(i)]["R_HC"], np.float64)
        mp = dd.map_xyz(e, i)
        mem = dd.memory(e, i)
        nm = sum(len(m[2]) for m in mem)
        r0, r2 = dd.rows(e, "M0")[i], dd.rows(e, "M2")[i]
        boxes = [(40 + k * 560, yy, 40 + k * 560 + 540, yy + 380) for k in range(3)]
        titles = [f"{i}: map {len(mp):,} surfels", f"{i}: memory {nm:,} samples", f"{i}: effective {len(mp) + nm:,}"]
        chart_triplet(d, boxes, titles, mp, mem, r, r0["local_gaze_deg"], r2["local_gaze_deg"])
        tx = 40 + 3 * 560
        lines = [(f"entity {i}" + (" (rank 1)" if i in SP.RANK1 else ""), S.INK),
                 f"memory own {r2['own_memory_points']:,} / cross {r2['cross_memory_points']:,}",
                 f"revision M0 {r0['revision']} -> M2 {r2['revision']}",
                 f"M0: {r0['fsg6f']} / {r0['cyclopean']}", f"   eligible {r0['cyclopean_eligible']}, "
                                                            f"proposal {r0['source']} {fmt(r0['local_gaze_deg'])}",
                 f"M2: {r2['fsg6f']} / {r2['cyclopean']}", f"   eligible {r2['cyclopean_eligible']}, "
                                                            f"proposal {r2['source']} {fmt(r2['local_gaze_deg'])}",
                 f"state M0 {r0['label']} / M2 {r2['label']}",
                 "sources: " + sources_text(mem)]
        text_block(d, tx, yy + 10, lines, size=16, gap=30)
        out[str(i)] = {"map": int(len(mp)), "memory": int(nm), "sources": [[int(e_), int(t_)] for e_, t_, _x in mem]}
    return img, {"entities": out, "after_event": e}


def divergence_fig(dd: Data) -> tuple[Image.Image, dict]:
    img = Image.new("RGB", (W, 700), S.SURFACE)
    y = NV.header(img, "Decision divergence at the first causal difference", [SP.LABEL_NOT_EXECUTED],
                  BADGES["decision-divergence.png"])
    y, _ = panel_e(img, y, dd)
    return img.crop((0, 0, W, y + 30)), {"before_ns1c2_step": dd.div["before_ns1c2_step"]}


def reactivation_fig(dd: Data) -> tuple[Image.Image, dict]:
    re = dd.rp["natural_reactivations"]
    img = Image.new("RGB", (W, 260 + 60 * len(re)), S.SURFACE)
    y = NV.header(img, "Natural reactivation through the memory (no reactivation call)", [SP.LABEL_MEMORY],
                  BADGES["reactivation.png"])
    d = ImageDraw.Draw(img)
    for n, r in enumerate(re):
        S.text(d, (60, y + n * 60), f"entity {r['object']}: QUIET since step {r.get('quiet_since_step')} -> trigger "
                                    f"{r['trigger_target']} at step {r['global_step']}; probe before "
                                    f"{(r['probe_before'].get('cyclopean') or {}).get('eligible_cells')} -> after "
                                    f"{(r['probe_after'].get('cyclopean') or {}).get('eligible_cells')} eligible cells",
               size=S.T_SMALL)
    return img, {"reactivations": len(re)}


def render_all(run: Path) -> tuple[dict, Data]:
    dd = Data(run)
    figs = {"overview.png": overview(dd), "memory-causal-timeline.png": timeline(dd),
            "effective-geometry-before-after.png": before_after(dd)}
    if dd.div is not None:
        figs["decision-divergence.png"] = divergence_fig(dd)
    if dd.rp["natural_reactivations"]:
        figs["reactivation.png"] = reactivation_fig(dd)
    return figs, dd


def visualize(run: Path, vis: Path) -> dict:
    vis = Path(vis)
    vis.mkdir(parents=True, exist_ok=True)
    figs, dd = render_all(run)
    na = {"decision-divergence.png": "no action divergence occurred" if dd.div is None else None,
          "reactivation.png": "no natural reactivation occurred" if not dd.rp["natural_reactivations"] else None}
    man = {"schema": "NS1d-visuals-v1", "visual_language": "Visual Language 1", "run": str(run),
           "font_hashes": S.font_hashes(), "figures": {}, "not_applicable": {k: v for k, v in na.items() if v},
           "fixed_head_statement": SP.LABEL_FIXED_HEAD, "outcome_reading": dd.outcome(),
           "memory_vs_map": "memory samples are drawn as glyphs by source active target, never as fused surfels"}
    for name, (im, meta) in figs.items():
        path = vis / name
        im.save(path, format="PNG", optimize=False)
        man["figures"][name] = {"sha256": sha256(path), "size": list(im.size), "badges": BADGES[name],
                                "labels": LABELS[name], **meta}
    (vis / "visuals-manifest.json").write_text(json.dumps(man, indent=1, sort_keys=True) + "\n")
    return man
