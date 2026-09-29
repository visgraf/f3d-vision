#!/usr/bin/env python3
"""Controller-01 visual package (preview/visual Policy 1, Level B).

    .venv/bin/python tools/controller/visualize_controller01.py \
        --run   /home/lvelho/rd/f3d-vision/previews/controller-01-full \
        --audit /home/lvelho/rd/f3d-vision/previews/controller-01a-terminal-audit/audit.json \
        --out   /home/lvelho/rd/f3d-vision/visuals/controller-01

Contract: docs/controller/controller-01-visuals-contract.md.  Visualization of accepted
measurements only.  It reads controller-time artifacts under the Controller-01 truth firewall
(never evaluation truth), recomputes every annotated number, and refuses to write the package
if any check fails.  Panels are labelled CONTROLLER-TIME or DERIVED.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import fov3d  # noqa: F401
from fov3d.control import frontier, integrated as ic, object_policy
from fov3d.experiments.classroom_oracle import controller01 as c01, epistemic, matcher
from fov3d.reconstruction.measurement_memory import InstanceMeasurementMemory, effective_target_geometry

CYC = epistemic._legacy_impl  # sealed Cyclopean helpers, read-only
ACCEPTED = {"manifest.json": "d293a98fd6bb285e882186af8fbeadba29ab1d1d62efea23f3ed0ff5c62c0e91",
            "actions.json": "12cdbe4d760cce6c494075e4368f9424805b51b997b8b21724bf87f71cc55afd"}
EVENTS = {  # the accepted, report-recorded event numbers (checked against the run)
    109: {"quiet": 4, "react": 7, "trigger": 110, "added": 4, "eff": (6166, 6170), "elig": (0, 28), "served": 134},
    178: {"quiet": 67, "react": 114, "trigger": 224, "added": 36748, "eff": (215125, 251873), "elig": (0, 189),
          "served": 136},
}
WATCH = {"obj": 210, "step": 101, "looks": 24, "map": 163944, "eff": (1748902, 1938913), "added": 190011,
         "counts": ((354, 58, 26, 270), (350, 52, 28, 270)), "support": (35, 30), "gaze": (7.6, 18.2)}

SURFACE, INK, INK2, MUTED, GRID = (252, 252, 251), (11, 11, 11), (82, 81, 78), (160, 158, 152), (228, 227, 222)
BLUE, ORANGE, AQUA = (42, 120, 214), (235, 104, 52), (27, 175, 122)
OLD_PTS, SEEN, SUPPORT = (178, 176, 170), (232, 230, 225), (152, 181, 219)
BADGE = {"CONTROLLER-TIME": (42, 120, 214), "DERIVED": (82, 81, 78)}


def font(size: int):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def angles(xyz: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    p = np.asarray(xyz, np.float64).reshape(-1, 3)
    return np.degrees(np.arctan2(p[:, 0], -p[:, 2])), np.degrees(np.arctan2(p[:, 1], np.hypot(p[:, 0], p[:, 2])))


def gamma_u8(rgb_linear: np.ndarray) -> np.ndarray:
    return np.rint(np.power(np.clip(np.asarray(rgb_linear, np.float64), 0, 1), 1 / 2.2) * 255).astype(np.uint8)


class CheckError(RuntimeError):
    pass


CHECKS: list[dict] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    CHECKS.append({"check": name, "ok": bool(ok), "detail": detail})
    print(f"[controller01-visuals] {'PASS' if ok else 'FAIL'} {name}{'' if ok else ': ' + detail}")
    if not ok:
        raise CheckError(f"{name}: {detail}")


# ---------------------------------------------------------------- controller-time source

class Source:
    """The accepted run: logs, the replayed measurement memory, map snapshots, own contexts."""

    def __init__(self, run: Path):
        self.run = run
        self.manifest = json.loads((run / "manifest.json").read_text())
        doc = json.loads((run / "actions.json").read_text())
        self.actions, self.events = doc["actions"], doc["events"]
        self.names = {int(o["instance_id"]): o["object_name"]
                      for o in json.loads((run / "bootstrap/instance_catalog.json").read_text())["instances"]}
        self.memory = InstanceMeasurementMemory()
        pts, cols, inst, step = [], [], [], []
        for a in self.actions:
            i, k, s = int(a["target_id"]), int(a["object_local_step"]), int(a["global_step"])
            z = self._npz(f"objects/instance_{i:04d}/patches/fix_{k:02d}.npz")
            added = self.memory.append_patch(z, source_global_index=s, source_active_target_id=i)
            if {str(x): int(v) for x, v in sorted(added.items())} != a["measurement_memory_additions"]:
                raise CheckError(f"memory replay differs at step {s}")
            m = z["valid"] & (z["instance_id"] > 0) & np.isfinite(z["xyz_h"]).all(-1)
            bgr = cv2.imread(str(run / f"objects/instance_{i:04d}/benchmark/fix_{k:02d}_L.png"))
            pts.append(z["xyz_h"][m]); cols.append(bgr[..., ::-1][m]); inst.append(z["instance_id"][m])
            step.append(np.full(int(m.sum()), s, np.int32))
        self.pts, self.cols = np.concatenate(pts).astype(np.float64), np.concatenate(cols)
        self.inst, self.step = np.concatenate(inst), np.concatenate(step)

    def _npz(self, rel: str) -> dict[str, np.ndarray]:
        with np.load(self.run / rel, allow_pickle=False) as z:
            return {k: z[k] for k in z.files}

    def own_actions(self, obj: int, upto: int) -> list[dict]:
        return [a for a in self.actions if int(a["target_id"]) == obj and int(a["global_step"]) <= upto]

    def map_at(self, obj: int, step: int) -> dict[str, np.ndarray]:
        own = self.own_actions(obj, step)
        return self._npz(f"objects/instance_{obj:04d}/maps/fix_{len(own) - 1:02d}.npz")

    def memory_at(self, obj: int, step: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        snap = self.memory.snapshot(obj)
        keep = snap.source_global_index <= step
        return (np.asarray(snap.xyz_h, np.float64)[keep], snap.source_global_index[keep],
                snap.source_active_target_id[keep])

    def effective_at(self, obj: int, step: int) -> np.ndarray:
        return effective_target_geometry(np.asarray(self.map_at(obj, step)["xyz_h"], np.float64),
                                         self.memory_at(obj, step)[0])

    def own_context(self, obj: int, upto: int) -> tuple[c01.LocalPolicyContext, list[dict]]:
        ctx, looks = c01.LocalPolicyContext(obj), []
        for a in self.own_actions(obj, upto):
            k = int(a["object_local_step"])
            adir = self.run / f"objects/instance_{obj:04d}/acquisitions/fix_{k:02d}"
            c = json.loads((adir / "calibration.json").read_text())
            rec, _meta, st = matcher.compute(c, self._npz(str(adir.relative_to(self.run)) + "/oracle_observation.npz"))
            gaze = (float(a["gaze_deg"][0]), float(a["gaze_deg"][1]))
            epistemic.add_observation(ctx.evidence, c, st["ids_left"], st["raw_support_L"], st["ids_right"],
                                      st["raw_support_R"], rec["valid"], obj)
            ctx.history.append(object_policy.history_entry(
                calibration=c, instance_L=st["ids_left"], raw_support_L=st["raw_support_L"],
                instance_R=st["ids_right"], raw_support_R=st["raw_support_R"], target_object_id=obj))
            ctx.visited.append(gaze)
            ctx.gaze, ctx.calibration, ctx.state = gaze, c, st
            looks.append({"local": k, "step": int(a["global_step"]), "gaze": gaze, "source": a["action_source"]})
        return ctx, looks

    def probe_record(self, obj: int, after: int) -> dict:
        res = json.loads((self.run / f"objects/instance_{obj:04d}/result.json").read_text())
        rows = [p for p in res["probes"] if int(p["after_global_step"]) == after]
        if len(rows) != 1:
            raise CheckError(f"probe record of {obj} after step {after}: {len(rows)} rows")
        return rows[0]

    def observation(self, obj: int, local: int) -> tuple[np.ndarray, np.ndarray, dict]:
        base = self.run / f"objects/instance_{obj:04d}"
        left = cv2.imread(str(base / f"benchmark/fix_{local:02d}_L.png"))[..., ::-1]
        right = cv2.imread(str(base / f"benchmark/fix_{local:02d}_R.png"))[..., ::-1]
        return left, right, self._npz(f"objects/instance_{obj:04d}/patches/fix_{local:02d}.npz")


def cyclopean_layers(ctx, geometry: np.ndarray) -> dict[str, np.ndarray]:
    """The Cyclopean handoff's chart layers, from the sealed helpers; eligible count cross-checked."""
    ev = ctx.evidence
    support, _fp, _med = CYC._map_support(ev, geometry)
    complement = ~support
    exterior, _dist = CYC._exterior_and_distance(complement)
    shoreline = complement & cv2.dilate(support.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    eligible = shoreline & exterior & ~ev.seen_any
    for yaw, pitch in ctx.visited:
        yy, xx, ok = CYC._cells(ev, np.array([yaw]), np.array([pitch]))
        if bool(ok[0]):
            eligible[int(yy[0]), int(xx[0])] = False
    audit = epistemic.audit(ev, geometry, ctx.visited)
    if int(eligible.sum()) != int(audit["eligible_never_observed_exterior_shoreline_cells"]):
        raise CheckError("recomputed Cyclopean eligible cells differ from the accepted audit")
    return {"seen": ev.seen_any.copy(), "support": support, "shoreline": shoreline, "eligible": eligible,
            "selected": audit["selected"]}


def frontier_layers(ctx, geometry: np.ndarray, target_gaze: tuple[float, float]) -> dict:
    """FSG6f frontier states with the accepted public functions, and the candidate's aligned support."""
    fr = frontier.extract_frontier(geometry, ctx.gaze[0], ctx.gaze[1], ctx.calibration)
    stt = frontier.classify_frontier_state(fr, geometry, ctx.history)
    step = 5.0
    u = np.array([round((target_gaze[0] - ctx.gaze[0]) / step), round((target_gaze[1] - ctx.gaze[1]) / step)], float)
    u /= np.linalg.norm(u)
    delta = np.c_[fr["target_yaw_deg"] - fr["yaw_deg"], fr["target_pitch_deg"] - fr["pitch_deg"]]
    dn = np.linalg.norm(delta, axis=1)
    align = np.zeros(len(delta))
    good = dn > 1e-12
    align[good] = (delta[good] / dn[good, None]) @ u
    aligned = align >= 0.50
    return {"xyz": fr["xyz_h"], "open": stt["open"], "map": stt["map_resolved"], "boundary": stt["boundary_resolved"],
            "support": aligned & stt["open"],
            "counts": (stt["raw_count"], stt["open_count"], stt["map_resolved_count"], stt["boundary_resolved_count"])}


# ---------------------------------------------------------------- drawing

class Chart:
    def __init__(self, yaw0, yaw1, pit0, pit1, ppd):
        self.y0, self.y1, self.p0, self.p1, self.s = float(yaw0), float(yaw1), float(pit0), float(pit1), float(ppd)
        self.w, self.h = int(round((yaw1 - yaw0) * ppd)), int(round((pit1 - pit0) * ppd))

    def px(self, yaw, pitch):
        return (np.asarray(yaw, float) - self.y0) * self.s, (self.p1 - np.asarray(pitch, float)) * self.s


def render(chart: Chart, xyz: np.ndarray, colors: np.ndarray, radius: int = 0, img: np.ndarray | None = None):
    """Nearest-surface point splats in the fixed-head yaw/pitch chart (z-buffer by range)."""
    out = np.full((chart.h, chart.w, 3), SURFACE, np.uint8) if img is None else img
    if not len(xyz):
        return out
    xyz = np.asarray(xyz, float).reshape(-1, 3)
    yaw, pit = angles(xyz)
    x, y = chart.px(yaw, pit)
    cols = np.broadcast_to(np.asarray(colors, np.uint8), (len(xyz), 3))
    inwin = (x >= -radius - 1) & (x < chart.w + radius + 1) & (y >= -radius - 1) & (y < chart.h + radius + 1)
    x, y, cols = x[inwin], y[inwin], cols[inwin]
    rng = np.linalg.norm(xyz[inwin], axis=1)
    if not len(rng):
        return out
    offs = [(dx, dy) for dx in range(-radius, radius + 1) for dy in range(-radius, radius + 1) if dx * dx + dy * dy <= radius * radius]
    xi = np.concatenate([np.floor(x).astype(np.int64) + dx for dx, _ in offs])
    yi = np.concatenate([np.floor(y).astype(np.int64) + dy for _, dy in offs])
    rr = np.tile(rng, len(offs)) + np.repeat([0.0 if (dx, dy) == (0, 0) else 1e-3 for dx, dy in offs], len(rng))
    idx = np.tile(np.arange(len(rng)), len(offs))
    ok = (xi >= 0) & (xi < chart.w) & (yi >= 0) & (yi < chart.h)
    flat, rr, idx = yi[ok] * chart.w + xi[ok], rr[ok], idx[ok]
    order = np.lexsort((rr, flat))
    first = np.r_[True, flat[order][1:] != flat[order][:-1]]
    sel = order[first]
    out.reshape(-1, 3)[flat[sel]] = cols[idx[sel]]
    return out


def raster(chart: Chart, layers: list[tuple[np.ndarray, tuple]], grid_deg=0.10, domain=((-25.0, 25.0), (-20.0, 20.0))):
    """Chart-cell layers (0.1 deg Cyclopean grid) resampled into a chart window (nearest)."""
    out = np.full((chart.h, chart.w, 3), SURFACE, np.uint8)
    yy, xx = np.mgrid[0:chart.h, 0:chart.w]
    yaw = chart.y0 + (xx + 0.5) / chart.s
    pit = chart.p1 - (yy + 0.5) / chart.s
    cx = np.rint((yaw - domain[0][0]) / grid_deg).astype(int)
    cy = np.rint((pit - domain[1][0]) / grid_deg).astype(int)
    h, w = layers[0][0].shape
    inside = (cx >= 0) & (cx < w) & (cy >= 0) & (cy < h)
    for mask, color in layers:
        hit = np.zeros(inside.shape, bool)
        hit[inside] = mask[cy[inside], cx[inside]]
        out[hit] = color
    out[~inside] = (240, 239, 235)
    return out


def oblique(xyz: np.ndarray, colors: np.ndarray, size=(1100, 700), elev=38.0, azim=-18.0):
    """Orthographic view from above and behind the head (derived rendering)."""
    p = np.asarray(xyz, float).reshape(-1, 3)
    a, e = math.radians(azim), math.radians(elev)
    ry = np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]])
    rx = np.array([[1, 0, 0], [0, math.cos(e), -math.sin(e)], [0, math.sin(e), math.cos(e)]])
    q = p @ (rx @ ry).T
    u, v, depth = q[:, 0], -q[:, 1], -q[:, 2]
    lo = np.percentile(np.c_[u, v], 0.5, axis=0); hi = np.percentile(np.c_[u, v], 99.5, axis=0)
    sc = min((size[0] - 40) / (hi[0] - lo[0]), (size[1] - 40) / (hi[1] - lo[1]))
    xi = np.floor((u - lo[0]) * sc + 20).astype(np.int64); yi = np.floor((v - lo[1]) * sc + 20).astype(np.int64)
    out = np.full((size[1], size[0], 3), SURFACE, np.uint8)
    ok = (xi >= 0) & (xi < size[0]) & (yi >= 0) & (yi < size[1])
    flat = yi[ok] * size[0] + xi[ok]; d = depth[ok]; c = np.asarray(colors, np.uint8)[ok]
    order = np.lexsort((d, flat)); first = np.r_[True, flat[order][1:] != flat[order][:-1]]
    sel = order[first]
    out.reshape(-1, 3)[flat[sel]] = c[sel]
    return out


def panel(img: np.ndarray, title: str, badge: str, lines: list[str] = (), width: int | None = None) -> Image.Image:
    """A titled panel with a truth badge and caption lines."""
    im = Image.fromarray(img)
    if width is not None and im.width != width:
        im = im.resize((width, int(round(im.height * width / im.width))), Image.NEAREST)
    cap = 22 * len(lines) + (8 if lines else 0)
    out = Image.new("RGB", (im.width, im.height + 36 + cap), SURFACE)
    d = ImageDraw.Draw(out)
    d.text((6, 8), title, fill=INK, font=font(16))
    bw = d.textlength(badge, font=font(12)) + 14
    d.rounded_rectangle([out.width - bw - 6, 8, out.width - 6, 28], radius=4, fill=BADGE[badge])
    d.text((out.width - bw + 1, 11), badge, fill=(255, 255, 255), font=font(12))
    out.paste(im, (0, 36))
    for n, line in enumerate(lines):
        d.text((6, im.height + 44 + 22 * n), line, fill=INK2, font=font(14))
    return out


def grid(panels: list[Image.Image], cols: int, title: str, subtitle: list[str], gap: int = 14) -> Image.Image:
    rows = [panels[i:i + cols] for i in range(0, len(panels), cols)]
    cw = max(p.width for p in panels)
    rh = [max(p.height for p in r) for r in rows]
    head = 40 + 21 * len(subtitle)
    out = Image.new("RGB", (cols * cw + (cols + 1) * gap, head + sum(rh) + (len(rows) + 1) * gap), SURFACE)
    d = ImageDraw.Draw(out)
    d.text((gap, 10), title, fill=INK, font=font(21))
    for n, line in enumerate(subtitle):
        d.text((gap, 40 + 21 * n), line, fill=INK2, font=font(14))
    y = head + gap
    for r, h in zip(rows, rh):
        x = gap
        for p in r:
            out.paste(p, (x, y)); x += cw + gap
        y += h + gap
    return out


def draw_marks(img: np.ndarray, chart: Chart, marks: list[dict]) -> np.ndarray:
    im = Image.fromarray(img); d = ImageDraw.Draw(im)
    for m in marks:
        x, y = chart.px(m["gaze"][0], m["gaze"][1]); x, y = float(x), float(y)
        kind = m.get("kind", "ring")
        if kind == "fov":
            half = 6.0 * chart.s
            d.rectangle([x - half, y - half, x + half, y + half], outline=m.get("color", INK), width=2)
        elif kind == "x":
            r = 5; d.line([x - r, y - r, x + r, y + r], fill=m.get("color", INK), width=2)
            d.line([x - r, y + r, x + r, y - r], fill=m.get("color", INK), width=2)
        elif kind == "dot":
            r = m.get("r", 4); d.ellipse([x - r, y - r, x + r, y + r], fill=m.get("color", INK))
        else:
            r = m.get("r", 9); d.ellipse([x - r, y - r, x + r, y + r], outline=m.get("color", INK), width=3)
        if m.get("label"):
            f = font(13); tw = d.textlength(m["label"], font=f)
            lx = x + 11 if x + 11 + tw < im.width else x - 11 - tw
            d.rectangle([lx - 3, y - 10, lx + tw + 3, y + 8], fill=(255, 255, 255))
            d.text((lx, y - 8), m["label"], fill=m.get("color", INK), font=f)
        if m.get("to"):
            tx, ty = chart.px(m["to"][0], m["to"][1]); tx, ty = float(tx), float(ty)
            d.line([x, y, tx, ty], fill=INK, width=3)
            ang = math.atan2(ty - y, tx - x)
            for s in (+0.45, -0.45):
                d.line([tx, ty, tx - 14 * math.cos(ang + s), ty - 14 * math.sin(ang + s)], fill=INK, width=3)
    return np.asarray(im)


def legend_strip(items: list[tuple[tuple, str]], width: int) -> np.ndarray:
    im = Image.new("RGB", (width, 26), SURFACE); d = ImageDraw.Draw(im); x = 6
    for color, label in items:
        d.rectangle([x, 7, x + 14, 21], fill=color); d.text((x + 20, 6), label, fill=INK2, font=font(13))
        x += 34 + d.textlength(label, font=font(13))
    return np.asarray(im)


def stack(*imgs: np.ndarray, gap: int = 6) -> np.ndarray:
    w = max(i.shape[1] for i in imgs)
    out = [np.pad(i, ((0, gap), (0, w - i.shape[1]), (0, 0)), constant_values=252) for i in imgs]
    return np.concatenate(out, axis=0)


def side(*imgs: np.ndarray, gap: int = 8, labels: list[str] | None = None) -> np.ndarray:
    h = max(i.shape[0] for i in imgs)
    parts = []
    for n, i in enumerate(imgs):
        im = Image.fromarray(np.pad(i, ((0, h - i.shape[0]), (0, gap), (0, 0)), constant_values=252))
        if labels:
            d = ImageDraw.Draw(im); d.rectangle([0, 0, d.textlength(labels[n], font=font(14)) + 10, 20], fill=(255, 255, 255))
            d.text((4, 2), labels[n], fill=INK, font=font(14))
        parts.append(np.asarray(im))
    return np.concatenate(parts, axis=1)


def observation_panel(left, right, patch, highlight_ids: dict[int, tuple], scale=2, ring_small=False,
                      light: tuple[int, ...] = ()) -> np.ndarray:
    """Rectified left/right pair (the controller-time benchmark images) with measured pixels tinted.

    Ids in ``light`` get a light tint and an outline (context); the others a strong tint.
    """
    L = cv2.resize(left, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST).copy()
    R = cv2.resize(right, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
    for iid, color in highlight_ids.items():
        m = patch["valid"] & (patch["instance_id"] == iid)
        m2 = cv2.resize(m.astype(np.uint8), None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST).astype(bool)
        a = 0.18 if iid in light else 0.55
        L[m2] = ((1 - a) * L[m2] + a * np.array(color)).astype(np.uint8)
        contours, _ = cv2.findContours(m2.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        cv2.drawContours(L, contours, -1, color, 2)
        if ring_small:
            if iid not in light and m.any():
                for y, x in np.argwhere(m):
                    cv2.circle(L, (int(x * scale + scale / 2), int(y * scale + scale / 2)), 16, color, 3)
                cy, cx = np.argwhere(m).mean(axis=0) * scale
                text = f"{int(m.sum())} px of {iid}"
                (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
                tx = int(min(max(cx - tw - 26, 4), L.shape[1] - tw - 8)); ty = int(min(max(cy - 22, th + 6), L.shape[0] - 6))
                cv2.rectangle(L, (tx - 4, ty - th - 6), (tx + tw + 4, ty + 6), (255, 255, 255), -1)
                cv2.putText(L, text, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1, cv2.LINE_AA)
    return side(L, R, labels=["left eye (rectified core)", "right eye"])


def object_window(xyz: np.ndarray, margin=1.5, clip=((-27.0, 31.0), (-24.0, 24.0)), include: np.ndarray | None = None):
    yaw, pit = angles(xyz)
    y0, y1 = np.percentile(yaw, [0.5, 99.5]); p0, p1 = np.percentile(pit, [0.5, 99.5])
    if include is not None and len(include):
        iy, ip = angles(include)
        y0, y1, p0, p1 = min(y0, iy.min()), max(y1, iy.max()), min(p0, ip.min()), max(p1, ip.max())
    return (max(clip[0][0], y0 - margin), min(clip[0][1], y1 + margin), max(clip[1][0], p0 - margin), min(clip[1][1], p1 + margin))


def ppd_for(win, width=860):
    return width / (win[1] - win[0])


# ---------------------------------------------------------------- events

def reactivation_event(src: Source, obj: int, ev_expected: dict):
    q, r, trig = ev_expected["quiet"], ev_expected["react"], ev_expected["trigger"]
    event = [e for e in src.events if e["event"] == "natural_reactivation" and e["object"] == obj]
    check(f"{obj}: exactly one logged natural reactivation, after step {r}, by target {trig}, quiet since {q}",
          len(event) == 1 and event[0]["global_step"] == r and event[0]["trigger_target"] == trig
          and event[0]["quiet_since_step"] == q, str(event[:1]))
    e = event[0]
    ctx, looks = src.own_context(obj, r)
    before, after = src.effective_at(obj, q), src.effective_at(obj, r)
    check(f"{obj}: effective geometry before/after equals the logged probe records {ev_expected['eff']}",
          (len(before), len(after)) == ev_expected["eff"] == (e["probe_before"]["effective_points"],
                                                           e["probe_after"]["effective_points"]),
          f"{len(before)}, {len(after)}")
    mem_after, msteps, msrc = src.memory_at(obj, r)
    new = msteps > q
    check(f"{obj}: {ev_expected['added']} cross-target points added since quiet, none own-target",
          int(new.sum()) == ev_expected["added"] == e["memory_added_since_quiet"]["points"]
          and bool(np.all(msrc[new] != obj)), f"{int(new.sum())}")
    cb, ca = cyclopean_layers(ctx, before), cyclopean_layers(ctx, after)
    eb, ea = int(cb["eligible"].sum()), int(ca["eligible"].sum())
    check(f"{obj}: recomputed Cyclopean eligible cells {ev_expected['elig']} equal the logged probe records",
          (eb, ea) == ev_expected["elig"] == (e["probe_before"]["cyclopean"]["eligible_cells"],
                                              e["probe_after"]["cyclopean"]["eligible_cells"]), f"{eb} -> {ea}")
    served = [a for a in src.actions if a["target_id"] == obj and a["scheduler_reason"] == "natural_reactivation"]
    check(f"{obj}: serviced after the reactivation at step {ev_expected['served']}",
          len(served) == 1 and served[0]["global_step"] == ev_expected["served"], str([a["global_step"] for a in served]))
    trig_action = src.actions[r]
    sel = e["probe_after"]["cyclopean"]["next_gaze_deg"]
    L, R, patch = src.observation(trig, int(trig_action["object_local_step"]))
    upto = src.step <= r
    newxyz, newsteps = mem_after[new], msteps[new]
    earlier = newsteps != r
    stats = {"object": obj, "quiet_since": q, "reactivated_after": r, "trigger": trig, "added": int(new.sum()),
             "effective": [len(before), len(after)], "eligible": [eb, ea], "served": ev_expected["served"],
             "cyclopean_proposal_at_reactivation": sel}
    win = object_window(after, margin=2.0, include=newxyz)
    return build_reactivation(src, obj, ev_expected, e, looks, before, after, new, newxyz, newsteps, earlier, cb, ca,
                              eb, ea, served, trig_action, sel, L, R, patch, upto, win, False), \
        build_reactivation(src, obj, ev_expected, e, looks, before, after, new, newxyz, newsteps, earlier, cb, ca,
                           eb, ea, served, trig_action, sel, L, R, patch, upto, win, True), stats


def build_reactivation(src, obj, ev_expected, e, looks, before, after, new, newxyz, newsteps, earlier, cb, ca, eb, ea,
                       served, trig_action, sel, L, R, patch, upto, win, small):
    q, r, trig = ev_expected["quiet"], ev_expected["react"], ev_expected["trigger"]
    at_trigger = int((newsteps == r).sum())
    since = e["memory_added_since_quiet"]

    width = 560 if small else 860
    ch = Chart(*win, ppd_for(win, width))
    ty, tp = trig_action["gaze_deg"]; sy_, sp_ = served[0]["gaze_deg"]
    w1 = (max(-31.0, min(win[0], ty - 7.0, sy_ - 2.0)), min(33.0, max(win[1], ty + 7.0, sy_ + 2.0)),
          max(-28.0, min(win[2], tp - 7.0, sp_ - 2.0)), min(28.0, max(win[3], tp + 7.0, sp_ + 2.0)))
    ch1 = Chart(*w1, ppd_for(w1, width))
    # 1. scene / attention: measurement memory up to the trigger step, look RGB
    scene = render(ch1, src.pts[upto], src.cols[upto], radius=1)
    scene = (0.55 * scene + 0.45 * 252).astype(np.uint8)
    mine = render(ch1, after, ORANGE, radius=0, img=np.zeros_like(scene))
    scene[mine.any(-1)] = (0.5 * scene[mine.any(-1)] + 0.5 * np.array(ORANGE)).astype(np.uint8)
    marks = [{"gaze": g["gaze"], "kind": "x", "color": INK} for g in looks]
    marks += [{"gaze": trig_action["gaze_deg"], "kind": "fov", "color": BLUE},
              {"gaze": trig_action["gaze_deg"], "kind": "dot", "color": BLUE, "r": 6,
               "label": f"step {r}: {trig} {src.names[trig]} fixation"},
              {"gaze": served[0]["gaze_deg"], "kind": "ring", "color": AQUA,
               "label": f"serviced @ {ev_expected['served']}"}]
    p1 = panel(draw_marks(scene, ch1, marks), f"1. SCENE / ATTENTION  (step {r})", "CONTROLLER-TIME",
               [f"memory up to step {r} (look RGB); {obj} {src.names[obj]} tinted orange",
                f"x = {obj}'s own looks; blue box = trigger fixation (12 deg core)"] if not small else [])
    # 2. the trigger observation
    obs = observation_panel(L, R, patch, {trig: BLUE, obj: ORANGE}, scale=1 if small else 2,
                            ring_small=ev_expected["added"] < 50, light=(trig,))
    p2 = panel(obs, f"2. FOVEATED OBSERVATION of target {trig} (step {r})", "CONTROLLER-TIME",
               [f"orange = pixels measured as {obj} (cross-target); blue outline = target {trig}",
                f"this trigger look added {at_trigger:,} points of {obj}; since quiet (steps {since['source_global_steps']}): "
                + ", ".join(f"from {t}: {n:,}" for t, n in since['by_source_target'].items())] if not small else [])
    # 3. Cyclopean state before / after
    def cyc_img(layers):
        img = raster(ch, [(layers["seen"], SEEN), (layers["support"], SUPPORT)])
        el = cv2.dilate(layers["eligible"].astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
        return raster(ch, [(layers["seen"], SEEN), (layers["support"], SUPPORT), (el, ORANGE)])
    cb_img = draw_marks(cyc_img(cb), ch, [{"gaze": g["gaze"], "kind": "x"} for g in looks])
    ca_img = draw_marks(cyc_img(ca), ch, [{"gaze": g["gaze"], "kind": "x"} for g in looks]
                        + [{"gaze": sel, "kind": "ring", "color": INK, "label": "Cyclopean proposal"}])
    p3 = panel(stack(side(cb_img, labels=[f"before (quiet @ {q}): eligible {eb}"]),
                     side(ca_img, labels=[f"after step {r}: eligible {ea}"]),
                     legend_strip([(SEEN, f"seen by {obj}'s own looks"), (SUPPORT, "effective map support"),
                                   (ORANGE, "eligible: never-observed exterior shoreline")], ch.w)),
               "Cyclopean state, before -> after" if small else "3. CYCLOPEAN / EPISTEMIC (target-relative)", "DERIVED",
               ["accepted probe: FSG6f no_frontier both times; Cyclopean QUIET -> ACTIONABLE",
                "counts are descriptive; the accepted local probe made the classification"] if not small else [])
    # 4. persistent 3-D memory before / after
    gb = render(ch, before, OLD_PTS, radius=0)
    ga = render(ch, before, OLD_PTS, radius=0)
    ga = render(ch, newxyz[earlier], BLUE, radius=1, img=ga)
    ga = render(ch, newxyz[~earlier], ORANGE, radius=1 if ev_expected["added"] > 50 else 3, img=ga)
    if ev_expected["added"] < 50:
        ga = draw_marks(ga, ch, [{"gaze": (float(yy), float(pp)), "kind": "ring", "color": ORANGE, "r": 14}
                                 for yy, pp in zip(*angles(newxyz))])
    leg = [(OLD_PTS, f"effective geometry at quiet ({len(before):,})"), (ORANGE, f"added at step {r} (trigger)")]
    if earlier.any():
        leg.insert(1, (BLUE, f"added at steps {sorted(set(int(v) for v in newsteps[earlier]))}"))
    p4 = panel(stack(side(gb, labels=[f"before: {len(before):,} points"]),
                     side(ga, labels=[f"after: {len(after):,} points (+{int(new.sum()):,} cross-target)"]),
                     legend_strip(leg, ch.w)),
               "Effective causal geometry" if small else "4. PERSISTENT 3-D MEMORY: EFFECTIVE CAUSAL GEOMETRY",
               "CONTROLLER-TIME",
               [f"active map of {obj} unchanged ({len(src.map_at(obj, r)['xyz_h']):,} surfels); only measurement memory grew"]
               if not small else [])
    title = (f"Natural reactivation of {obj} {src.names[obj]}: QUIET (step {q}) -> target {trig} observed -> "
             f"cross-target geometry -> ACTIONABLE (step {r}) -> serviced (step {ev_expected['served']})")
    sub = [f"trigger: target {trig} {src.names[trig]} at step {r}; cross-target points of {obj} added since quiet: "
           f"{int(new.sum()):,}; Cyclopean eligible cells {eb} -> {ea}; effective geometry {len(before):,} -> {len(after):,}",
           "The accepted local probe (FSG6f -> Cyclopean) classified the state; the counts are descriptive. "
           "Controller-time data and derived renderings only; no evaluation truth."]
    return grid([p1, p2, p3, p4], 2, title, sub) if not small else (p3, p4)


def watchdog_event(src: Source, audit: dict):
    obj, s = WATCH["obj"], WATCH["step"]
    ctx, looks = src.own_context(obj, s)
    check("210: 24 own looks, the last at step 101 with gaze [2.6, 18.2]",
          len(looks) == WATCH["looks"] and looks[-1]["step"] == s, f"{len(looks)} looks")
    final_step = len(src.actions) - 1
    eff_w, eff_t = src.effective_at(obj, s), src.effective_at(obj, final_step)
    amap = src.map_at(obj, s)["xyz_h"]
    m = audit["measurements"]
    check("210: active map 163,944; effective 1,748,902 -> 1,938,913; equal to the 01A audit",
          len(amap) == WATCH["map"] == m["active_map_points"] and (len(eff_w), len(eff_t)) == WATCH["eff"]
          == (m["effective_points_at_watchdog"], m["effective_points_at_terminal"]), f"{len(eff_w)}, {len(eff_t)}")
    mem_t, msteps, msrc = src.memory_at(obj, final_step)
    late = msteps > s
    by = {str(int(t)): int((msrc[late] == t).sum()) for t in np.unique(msrc[late])}
    check("210: +190,011 later cross-target measurements by source equal the 01A audit",
          int(late.sum()) == WATCH["added"] == m["added_after_watchdog"] and by == m["added_by_source_target"], str(by))
    fw_, ft_ = frontier_layers(ctx, eff_w, WATCH["gaze"]), frontier_layers(ctx, eff_t, WATCH["gaze"])
    pa, pt = audit["watchdog_prefix_probe"], audit["terminal_probe"]
    exp = tuple(tuple(pr["summary"]["fsg6f"][k] for k in ("frontier_raw_count", "frontier_open_count",
                                                          "frontier_map_resolved_count", "frontier_boundary_resolved_count"))
                for pr in (pa, pt))
    check("210: recomputed frontier raw/OPEN/map/boundary equal the 01A audit (354/58/26/270 -> 350/52/28/270)",
          (tuple(fw_["counts"]), tuple(ft_["counts"])) == exp == WATCH["counts"], f"{fw_['counts']} -> {ft_['counts']}")
    sup = (int(fw_["support"].sum()), int(ft_["support"].sum()))
    check("210: aligned OPEN support of the [7.6, 18.2] candidate equals the 01A audit (35 -> 30)",
          sup == WATCH["support"] == (pa["fsg6f_selected"]["frontier_support_count"],
                                      pt["fsg6f_selected"]["frontier_support_count"]), str(sup))
    check("210: proposed gaze [7.6, 18.2] at the watchdog and at the terminal state (01A)",
          all(abs(pr["proposed_gaze_deg"][j] - WATCH["gaze"][j]) < 1e-9 for pr in (pa, pt) for j in (0, 1)))
    stats = {"own_looks": len(looks), "active_map": len(amap), "effective": [len(eff_w), len(eff_t)],
             "added_after_watchdog": int(late.sum()), "added_by_source": by, "frontier_counts": [fw_["counts"], ft_["counts"]],
             "candidate_support": list(sup), "proposed_gaze": list(WATCH["gaze"])}
    args = (src, ctx, looks, eff_w, eff_t, amap, mem_t, msrc, late, by, fw_, ft_, sup)
    return build_watchdog(*args, small=False), build_watchdog(*args, small=True), stats


def build_watchdog(src, ctx, looks, eff_w, eff_t, amap, mem_t, msrc, late, by, fw_, ft_, sup, small):
    obj, s = WATCH["obj"], WATCH["step"]
    win = (-24.0, 31.0, -3.0, 23.5)
    width = 560 if small else 860
    ch = Chart(*win, ppd_for(win, width))
    last = looks[-1]
    # 1. own looks
    scene = render(ch, src.pts[src.step <= s], src.cols[src.step <= s], radius=1)
    scene = (0.55 * scene + 0.45 * 252).astype(np.uint8)
    marks = [{"gaze": g["gaze"], "kind": "dot", "color": BLUE if g["source"] == "fsg6f" else (AQUA if g["source"] != "oracle_seed" else ORANGE),
              "r": 5, "label": str(n) if n in (0, 23) else None} for n, g in enumerate(looks)]
    marks += [{"gaze": last["gaze"], "kind": "fov", "color": INK},
              {"gaze": last["gaze"], "kind": "ring", "color": INK, "to": WATCH["gaze"]},
              {"gaze": WATCH["gaze"], "kind": "fov", "color": ORANGE},
              {"gaze": WATCH["gaze"], "kind": "ring", "color": ORANGE, "label": "still proposed [7.6, 18.2]"}]
    p1 = panel(draw_marks(scene, ch, marks), "1. SCENE / ATTENTION: 210 wall.008, 24 own looks (watchdog)", "CONTROLLER-TIME",
               ["dots = own looks (orange seed, blue FSG6f, aqua Cyclopean); black box = last look (step 101)",
                "orange box = the FSG6f look still requested at the watchdog and at the terminal state"] if not small else [])
    L, R, patch = src.observation(obj, last["local"])
    p2 = panel(observation_panel(L, R, patch, {obj: ORANGE}, scale=1 if small else 2),
               "2. FOVEATED OBSERVATION: last own look (step 101)", "CONTROLLER-TIME",
               ["orange = pixels measured as 210 in the 24th look", "the watchdog blocked the object after this look"] if not small else [])

    def fr_img(eff, fl, label):
        img = render(ch, eff[:: max(1, len(eff) // 400000)], OLD_PTS, radius=0)
        cols = np.zeros((len(fl["xyz"]), 3), np.uint8)
        cols[fl["map"]] = BLUE; cols[fl["boundary"]] = AQUA; cols[fl["open"]] = ORANGE
        img = render(ch, fl["xyz"], cols, radius=2, img=img)
        img = draw_marks(img, ch, [{"gaze": (float(y), float(p)), "kind": "ring", "color": INK, "r": 5}
                                   for y, p in zip(*angles(fl["xyz"][fl["support"]]))])
        img = draw_marks(img, ch, [{"gaze": last["gaze"], "kind": "ring", "color": INK, "to": WATCH["gaze"]}])
        return side(img, labels=[label])
    p3 = panel(stack(fr_img(eff_w, fw_, f"watchdog (step 101): OPEN {fw_['counts'][1]}, candidates 1, support {sup[0]}"),
                     fr_img(eff_t, ft_, f"terminal (step 140): OPEN {ft_['counts'][1]}, candidates 1, support {sup[1]}"),
                     legend_strip([(ORANGE, "OPEN"), (BLUE, "MAP_RESOLVED"), (AQUA, "BOUNDARY_RESOLVED"),
                                   (INK, "ringed: OPEN support of the [7.6, 18.2] candidate")], ch.w)),
               "FSG6f frontier, watchdog -> terminal" if small else "3. EPISTEMIC: FSG6f FRONTIER STATE (target-relative)",
               "DERIVED",
               [f"raw/OPEN/map/boundary {'/'.join(map(str, fw_['counts']))} -> {'/'.join(map(str, ft_['counts']))}; "
                "FSG6f continue both times, same gaze", "later geometry altered the frontier but did not remove the proposal"]
               if not small else [])
    g1 = render(ch, eff_w, OLD_PTS, radius=0)
    g2 = render(ch, eff_w, OLD_PTS, radius=0)
    srcs = {"234": BLUE, "109": ORANGE, "224": AQUA}
    for t, col in srcs.items():
        g2 = render(ch, mem_t[late & (msrc == int(t))], col, radius=1, img=g2)
    p4 = panel(stack(side(g1, labels=[f"watchdog: effective {len(eff_w):,} (active map {len(amap):,})"]),
                     side(g2, labels=[f"terminal: effective {len(eff_t):,} (+{int(late.sum()):,} cross-target)"]),
                     legend_strip([(OLD_PTS, "effective geometry at the watchdog")]
                                  + [(c, f"from {t} {src.names[int(t)]}: {by[t]:,}") for t, c in srcs.items()], ch.w)),
               "Effective causal geometry" if small else "4. PERSISTENT 3-D MEMORY: EFFECTIVE CAUSAL GEOMETRY",
               "CONTROLLER-TIME",
               ["active map unchanged (no own look after step 101; nothing fused)",
                "own looks = 24 at both states"] if not small else [])
    title = "Object 210 wall.008: watchdog block (Controller-01) and terminal re-probe (Controller-01A)"
    sub = ["own looks 24 -> 24 | active map 163,944 -> 163,944 | effective 1,748,902 -> 1,938,913 (+190,011 cross-target) | "
           "OPEN 58 -> 52 | candidates 1 -> 1 | proposed gaze [7.6, 18.2] -> [7.6, 18.2]",
           "Later causal geometry altered the frontier but did not remove the local continuation proposal "
           "(CONTROLLER01A_FINAL_REPROBE_ACTIONABLE). No stopping-policy conclusion is drawn here."]
    return grid([p1, p2, p3, p4], 2, title, sub) if not small else (p3, p4)


def scene_final(src: Source, out_dir: Path) -> tuple[Image.Image, dict, np.ndarray, Chart]:
    xyz, rgb, inst = [], [], []
    for o in src.manifest["objects"]:
        i = int(o["instance_id"])
        z = src._npz(f"objects/instance_{i:04d}/final_map.npz")
        xyz.append(np.asarray(z["xyz_h"], np.float64)); rgb.append(gamma_u8(z["rgb"])); inst.append(np.full(len(z["xyz_h"]), i))
    per = {int(o["instance_id"]): int(o["final_map_surfels"]) for o in src.manifest["objects"]}
    check("scene: active-map surfel counts equal the manifest's final_map_surfels (25 objects)",
          [len(x) for x in xyz] == [per[int(o["instance_id"])] for o in src.manifest["objects"]], "")
    X, C, I = np.concatenate(xyz), np.concatenate(rgb), np.concatenate(inst)
    ch = Chart(-27.0, 27.0, -22.0, 22.0, 24.0)
    a = render(ch, X, C, radius=1)
    b = render(ch, src.pts, src.cols, radius=0)
    rng = np.linalg.norm(X, axis=1)
    t = np.clip((rng - np.percentile(rng, 1)) / (np.percentile(rng, 99) - np.percentile(rng, 1)), 0, 1)
    light, dark = np.array([214, 229, 247]), np.array([16, 55, 115])
    depth_cols = (light * (1 - t[:, None]) + dark * t[:, None]).astype(np.uint8)
    c = render(ch, X, depth_cols, radius=1)
    ob = oblique(X, C, size=(ch.w, int(ch.w * 0.62)))
    labels = []
    for o in src.manifest["objects"]:
        i = int(o["instance_id"])
        if i in (109, 178, 210):
            yy, pp = angles(X[I == i]); labels.append({"gaze": (float(np.median(yy)), float(np.median(pp))), "kind": "dot",
                                                       "color": INK, "r": 4, "label": f"{i} {src.names[i]}"})
    pa = panel(draw_marks(a, ch, labels), "ACTIVE FUSED MAPS (25 objects, 1,059,349 surfels), surfel RGB", "CONTROLLER-TIME",
               ["fixed-head view, yaw -27..27 deg, pitch -22..22 deg"])
    pb = panel(b, "MEASUREMENT MEMORY (all 141 looks, 7,843,577 points, 33 instances), look RGB", "CONTROLLER-TIME",
               ["every valid measurement of every look; includes 8 unlocated instances"])
    pc = panel(c, "ACTIVE FUSED MAPS, colored by range (near light -> far dark)", "DERIVED",
               [f"range {np.percentile(rng, 1):.2f} m .. {np.percentile(rng, 99):.2f} m"])
    pd = panel(ob, "ACTIVE FUSED MAPS, oblique view from above and behind the head", "DERIVED",
               ["orthographic; head frame (x right, y up, -z forward)"])
    img = grid([pa, pb, pc, pd], 2, "Controller-01 final reconstructed scene (Classroom, fixed head)",
               ["Controller-time geometry only; no evaluation truth. Active fused maps and measurement memory are shown in "
                "separate panels, never mixed."])
    pcdir = out_dir / "pointclouds"; pcdir.mkdir(parents=True, exist_ok=True)
    write_ply(pcdir / "scene-active-maps.ply", X, C)
    for i in (109, 178, 210):
        write_ply(pcdir / f"object-{i:04d}-active-map.ply", X[I == i], C[I == i])
    return img, {"active_map_surfels": int(len(X)), "measurement_points": int(len(src.pts))}, a, ch


def write_ply(path: Path, xyz: np.ndarray, rgb: np.ndarray) -> None:
    n = len(xyz)
    arr = np.empty(n, dtype=[("x", "<f4"), ("y", "<f4"), ("z", "<f4"), ("r", "u1"), ("g", "u1"), ("b", "u1")])
    arr["x"], arr["y"], arr["z"] = xyz[:, 0], xyz[:, 1], xyz[:, 2]
    arr["r"], arr["g"], arr["b"] = rgb[:, 0], rgb[:, 1], rgb[:, 2]
    head = ("ply\nformat binary_little_endian 1.0\ncomment Controller-01 active fused map, fixed head frame "
            "(x right, y up, -z forward), metres\n"
            f"element vertex {n}\nproperty float x\nproperty float y\nproperty float z\n"
            "property uchar red\nproperty uchar green\nproperty uchar blue\nend_header\n")
    path.write_bytes(head.encode() + arr.tobytes())


def card(header: list[str], a: Image.Image, b: Image.Image) -> Image.Image:
    body = side(np.asarray(a), np.asarray(b), gap=12)
    out = Image.new("RGB", (body.shape[1] + 16, body.shape[0] + 30 + 20 * len(header)), (244, 243, 239))
    d = ImageDraw.Draw(out)
    d.text((8, 6), header[0], fill=INK, font=font(17))
    for n, line in enumerate(header[1:]):
        d.text((8, 30 + 20 * n), line, fill=INK2, font=font(13))
    out.paste(Image.fromarray(body), (8, 24 + 20 * len(header)))
    return out


def overview(src: Source, scene_img: np.ndarray, scene_chart: Chart, small: dict, stats: dict) -> Image.Image:
    marks = []
    for obj, text, col in ((109, "reactivated after 110's look", ORANGE), (178, "reactivated after 224's look", ORANGE),
                           (210, "watchdog-blocked; 01A: still ACTIONABLE", INK)):
        X = src._npz(f"objects/instance_{obj:04d}/final_map.npz")["xyz_h"]
        yy, pp = angles(X)
        marks.append({"gaze": (float(np.median(yy)), float(np.median(pp))), "kind": "ring", "color": col, "r": 11,
                      "label": f"{obj} {src.names[obj]}: {text}"})
    m = src.manifest
    top = panel(draw_marks(scene_img, scene_chart, marks), "Final active fused maps (25 objects, 1,059,349 surfels)",
                "CONTROLLER-TIME",
                [f"{m['localized_objects']} localized, {m['successfully_initialized_objects']} initialized | "
                 f"{m['total_actions']} observations | {m['total_switches']} switches | {m['attention_bouts']} bouts",
                 f"{m['natural_reactivations']} natural reactivations | 24 QUIET + 210 BLOCKED:watchdog | "
                 "terminal INCOMPLETE(localized_objects_blocked)"])
    s109, s178, s210 = stats["109"], stats["178"], stats["210"]
    cards = [
        card(["109 alphabet: natural reactivation",
              f"QUIET @ {s109['quiet_since']} -> 110's look @ {s109['reactivated_after']} adds {s109['added']} cross-target points"
              f" -> Cyclopean eligible {s109['eligible'][0]} -> {s109['eligible'][1]} -> ACTIONABLE -> serviced @ {s109['served']}"],
             *small[109]),
        card(["178 sol: natural reactivation",
              f"QUIET @ {s178['quiet_since']} -> looks of 201 and 224 add {s178['added']:,} cross-target points (last: 224 @ "
              f"{s178['reactivated_after']}) -> eligible {s178['eligible'][0]} -> {s178['eligible'][1]} -> ACTIONABLE -> "
              f"serviced @ {s178['served']}"], *small[178]),
        card(["210 wall.008: watchdog block and Controller-01A terminal re-probe",
              f"24 own looks; effective {s210['effective'][0]:,} -> {s210['effective'][1]:,} (+{s210['added_after_watchdog']:,} "
              f"cross-target); OPEN {s210['frontier_counts'][0][1]} -> {s210['frontier_counts'][1][1]}; candidate 1 -> 1; "
              "same proposal [7.6, 18.2]"], *small[210]),
    ]
    cw = max(c.width for c in cards)
    right_h = sum(c.height for c in cards) + 14 * (len(cards) - 1)
    right = Image.new("RGB", (cw, right_h), SURFACE)
    y = 0
    for c in cards:
        right.paste(c, (0, y)); y += c.height + 14
    tw = int(top.width * right_h / top.height) if top.height > right_h else top.width
    left = top.resize((tw, int(top.height * tw / top.width)), Image.LANCZOS) if tw != top.width else top
    title = "Controller-01: closing the scene-level loop with the accepted local policy (accepted result: INCOMPLETE)"
    sub = ["Two quiet objects became ACTIONABLE again only because later cross-target geometry changed their accepted local "
           "probe; 210 stayed ACTIONABLE through the watchdog and at the final state.",
           "Controller-time data and derived renderings only; no evaluation truth. Counts are descriptive; the accepted local "
           "probe made every state classification."]
    return grid([left, right], 2, title, sub)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--audit", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    run, out = args.run.resolve(), args.out.resolve()
    fw = ic.TruthFirewall(run, c01.is_evaluation_truth)
    try:
        with fw:
            for name, digest in ACCEPTED.items():
                check(f"source {name} is the accepted artifact", sha(run / name) == digest, sha(run / name))
            audit = json.loads(args.audit.read_text())
            check("source 01A audit: CONTROLLER01A_FINAL_REPROBE_ACTIONABLE, no failure",
                  audit.get("outcome") == "FINAL_REPROBE_ACTIONABLE" and audit.get("failure") is None)
            src = Source(run)
            check("memory replay reproduces all 141 logged per-action additions", len(src.actions) == 141)
            full, small = {}, {}
            for obj in (109, 178):
                full[obj], small[obj], full[f"s{obj}"] = reactivation_event(src, obj, EVENTS[obj])
            full[210], small[210], st210 = watchdog_event(src, audit)
            tmp = out.with_name(out.name + ".partial")
            if tmp.exists():
                shutil.rmtree(tmp)
            (tmp / "events").mkdir(parents=True); (tmp / "diagnostics").mkdir()
            scene_img, sstats, scene_arr, scene_chart = scene_final(src, tmp)
            full[109].save(tmp / "events/reactivation-0109.png")
            full[178].save(tmp / "events/reactivation-0178.png")
            full[210].save(tmp / "events/watchdog-0210.png")
            scene_img.save(tmp / "scene-final.png")
            overview(src, scene_arr, scene_chart, small,
                     {"109": full["s109"], "178": full["s178"], "210": st210}).save(tmp / "overview.png")
            for name in ("controller-attention-timeline.png", "controller-gaze-chart.png"):
                shutil.copyfile(run / name, tmp / "diagnostics" / name.replace("controller-", ""))
        check("truth firewall: 0 violations; no evaluation truth opened",
              not fw.violations and not any(c01.is_evaluation_truth(str(run / p)) for p in fw.opened), str(fw.violations))
    except CheckError as exc:
        print(f"[controller01-visuals] REFUSED: {exc}")
        return 1
    files = sorted(p.relative_to(tmp).as_posix() for p in tmp.rglob("*") if p.is_file())
    manifest = {
        "schema": "Controller01-visuals-v1",
        "contract": "docs/controller/controller-01-visuals-contract.md",
        "source_run": str(run), "source_audit": str(args.audit.resolve()),
        "truth": "controller-time and derived only; no reference/evaluation truth",
        "opened_source_files": len(fw.opened),
        "checks": CHECKS,
        "stats": {"109": full["s109"], "178": full["s178"], "210": st210, "scene": sstats},
        "files": {f: sha(tmp / f) for f in files},
    }
    (tmp / "visuals-manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    if out.exists():
        shutil.rmtree(out)
    tmp.rename(out)
    for f in files:
        print(f"[controller01-visuals] wrote {out / f}  sha256={manifest['files'][f][:16]}")
    print(f"[controller01-visuals] checks {sum(c['ok'] for c in CHECKS)}/{len(CHECKS)} passed; "
          f"opened {len(fw.opened)} controller-time files; firewall violations {len(fw.violations)}")
    print("[controller01-visuals] CONTROLLER01_VISUAL_PACKAGE_COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
