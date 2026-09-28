#!/usr/bin/env python3
"""Inspectable Controller-01 visuals from controller-time artifacts only.

    .venv/bin/python tools/controller/plot_controller01.py --run previews/controller-01-full

Reads only ``manifest.json`` and ``actions.json`` of a completed run and writes two
regenerable previews into the run directory:

- ``controller-attention-timeline.png``: x = global action, y = object.  Marker shape and
  color give the action source (seed square, FSG6f circle, Cyclopean triangle); a thin line
  joins the actions of one attention bout; dashed connectors mark switches; ``Q`` marks a
  quiet entry, a ring marks a natural reactivation, a cross a block.
- ``controller-gaze-chart.png``: the executed gaze sequence in the yaw/pitch controller
  domain, labelled by global action, with each object's id at its seed.

Evaluation truth is never opened.  Drawn with Pillow; nothing is installed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SURFACE = (252, 252, 251)
INK = (11, 11, 11)
INK2 = (82, 81, 78)
MUTED = (160, 158, 152)
GRID = (230, 229, 225)
BAND = (242, 241, 237)
SOURCE_COLOR = {"oracle_seed": (235, 104, 52), "fsg6f": (42, 120, 214), "cyclopean_epistemic": (27, 175, 122)}
SOURCE_LABEL = {"oracle_seed": "bootstrap seed", "fsg6f": "FSG6f", "cyclopean_epistemic": "Cyclopean handoff"}


def font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow without scalable default font
        return ImageFont.load_default()


def marker(d: ImageDraw.ImageDraw, x: float, y: float, source: str, r: float = 5.0) -> None:
    c = SOURCE_COLOR[source]
    ring = r + 2
    if source == "oracle_seed":
        d.rectangle([x - ring, y - ring, x + ring, y + ring], fill=SURFACE)
        d.rectangle([x - r, y - r, x + r, y + r], fill=c)
    elif source == "fsg6f":
        d.ellipse([x - ring, y - ring, x + ring, y + ring], fill=SURFACE)
        d.ellipse([x - r, y - r, x + r, y + r], fill=c)
    else:
        big = [(x, y - ring - 1.5), (x - ring - 1, y + ring - 0.5), (x + ring + 1, y + ring - 0.5)]
        d.polygon(big, fill=SURFACE)
        d.polygon([(x, y - r - 1.5), (x - r - 0.5, y + r - 0.5), (x + r + 0.5, y + r - 0.5)], fill=c)


def dashed(d: ImageDraw.ImageDraw, x0, y0, x1, y1, color, dash=4) -> None:
    n = max(1, int(max(abs(x1 - x0), abs(y1 - y0)) // dash))
    for k in range(0, n, 2):
        a, b = k / n, min(1.0, (k + 1) / n)
        d.line([x0 + (x1 - x0) * a, y0 + (y1 - y0) * a, x0 + (x1 - x0) * b, y0 + (y1 - y0) * b], fill=color, width=1)


def cross(d: ImageDraw.ImageDraw, x: float, y: float, r: float = 5.0) -> None:
    d.line([x - r, y - r, x + r, y + r], fill=INK, width=2)
    d.line([x - r, y + r, x + r, y - r], fill=INK, width=2)


def legend(d: ImageDraw.ImageDraw, x: float, y: float, extra: list[tuple[str, str]]) -> None:
    """Source markers, then extra keys drawn as shapes: bout, switch, ring, cross, or a text glyph."""
    f = font(13)
    for s in ("oracle_seed", "fsg6f", "cyclopean_epistemic"):
        marker(d, x + 6, y + 8, s)
        d.text((x + 18, y), SOURCE_LABEL[s], fill=INK2, font=f)
        x += 30 + d.textlength(SOURCE_LABEL[s], font=f)
    for key, label in extra:
        cy = y + 8
        if key == "bout":
            d.line([x, cy, x + 16, cy], fill=INK2, width=2)
            x += 22
        elif key == "switch":
            dashed(d, x + 4, cy - 7, x + 4, cy + 7, MUTED, dash=3)
            x += 12
        elif key == "ring":
            d.ellipse([x, cy - 8, x + 16, cy + 8], outline=INK, width=2)
            x += 22
        elif key == "cross":
            cross(d, x + 6, cy)
            x += 16
        else:
            d.text((x, y), key, fill=INK, font=f)
            x += 6 + d.textlength(key, font=f)
        d.text((x, y), label, fill=INK2, font=f)
        x += 22 + d.textlength(label, font=f)


def headline(manifest: dict) -> str:
    t = manifest.get("terminal", {})
    return (f"terminal {t.get('type')} {t.get('reason')}  ·  actions {manifest.get('total_actions')}  ·  "
            f"switches {manifest.get('total_switches')}  ·  bouts {manifest.get('attention_bouts')}  ·  "
            f"quiet episodes {manifest.get('quiet_episodes')}  ·  natural reactivations "
            f"{manifest.get('natural_reactivations')}  ·  localized {manifest.get('localized_objects')}"
            f"{'  ·  SMOKE (plumbing only)' if manifest.get('smoke') else ''}")


def timeline(run: Path, manifest: dict, actions: list[dict], events: list[dict]) -> Path:
    names = {int(k): v["object_name"] for k, v in manifest["final_service_states"].items()}
    finals = manifest["final_service_states"]
    objs = sorted({int(a["target_id"]) for a in actions} | {int(k) for k in finals})
    row = {o: k for k, o in enumerate(objs)}
    n = max(1, len(actions))
    step = max(6, min(22, 2400 // n))
    left, top, rh = 250, 96, 24
    w = left + step * (n + 1) + 40
    h = top + rh * len(objs) + 70
    img = Image.new("RGB", (max(w, 1100), h), SURFACE)
    d = ImageDraw.Draw(img)
    f, fs = font(13), font(11)
    x_of = lambda t: left + step * (t + 0.5)
    y_of = lambda o: top + rh * (row[o] + 0.5)
    d.text((16, 12), f"Controller-01 attention timeline: {run.name}", fill=INK, font=font(18))
    d.text((16, 38), headline(manifest), fill=INK2, font=f)
    legend(d, 16, 62, [("bout", "attention bout"), ("switch", "switch"), ("Q", "quiet entry"),
                       ("ring", "natural reactivation"), ("cross", "blocked")])
    bouts: dict[int, list[dict]] = {}
    for a in actions:
        bouts.setdefault(int(a["attention_bout"]), []).append(a)
    for b, rows_b in bouts.items():
        if b % 2 == 0:
            d.rectangle([x_of(rows_b[0]["global_step"]) - step / 2, top, x_of(rows_b[-1]["global_step"]) + step / 2,
                         top + rh * len(objs)], fill=BAND)
    for o in objs:
        y = y_of(o)
        d.line([left, y, left + step * n, y], fill=GRID, width=1)
        st = finals.get(str(o), {})
        label = f"{o} {names.get(o, '')[:18]}"
        d.text((12, y - 8), label, fill=INK2, font=f)
        final = st.get("state", "") if st.get("blocked_reason") is None else f"BLOCKED:{st['blocked_reason']}"
        d.text((left - 8 - d.textlength(final, font=fs), y - 7), final, fill=MUTED, font=fs)
    for t in range(0, n + 1, 1 if n <= 20 else 5 if n <= 100 else 10 if n <= 200 else 25):
        x = left + step * t
        d.line([x, top + rh * len(objs), x, top + rh * len(objs) + 5], fill=INK2)
        d.text((x - 6, top + rh * len(objs) + 8), str(t), fill=INK2, font=fs)
    d.text((left, top + rh * len(objs) + 28), "global action (executed OBSERVE index)", fill=INK2, font=f)
    for b, rows_b in bouts.items():
        o = int(rows_b[0]["target_id"])
        if len(rows_b) > 1:
            d.line([x_of(rows_b[0]["global_step"]), y_of(o), x_of(rows_b[-1]["global_step"]), y_of(o)], fill=INK2, width=2)
    for a in actions:
        if a["scheduler_decision"] == "switch" and a["previous_object"] is not None:
            t = a["global_step"]
            dashed(d, x_of(t) - step / 2, y_of(int(a["previous_object"])), x_of(t) - step / 2, y_of(int(a["target_id"])), MUTED)
    for a in actions:
        marker(d, x_of(a["global_step"]), y_of(int(a["target_id"])), a["action_source"], r=max(3.5, min(5.0, step / 3)))
    for e in events:
        o, t = int(e["object"]), int(e["global_step"])
        x, y = x_of(t) + step / 2, y_of(o)
        if e["event"] == "quiet":
            d.text((x - 3, y - 20), "Q", fill=INK2, font=fs)
        elif e["event"] == "natural_reactivation":
            d.ellipse([x - 9, y - 9, x + 9, y + 9], outline=INK, width=2)
            d.text((x + 11, y - 20), f"reactivated by {e['trigger_target']} @ {t}", fill=INK, font=fs)
        elif e["event"] == "blocked":
            cross(d, x, y, 4.0)
            d.text((x + 8, y - 20), str(e["reason"]), fill=INK, font=fs)
    out = run / "controller-attention-timeline.png"
    img.save(out)
    return out


def gaze_chart(run: Path, manifest: dict, actions: list[dict], events: list[dict]) -> Path:
    dom = manifest["controller_domain_deg"]
    y0, y1 = map(float, dom["yaw"])
    p0, p1 = map(float, dom["pitch"])
    s = 26.0
    left, top = 70, 100
    w, h = int(left + (y1 - y0) * s + 60), int(top + (p1 - p0) * s + 70)
    img = Image.new("RGB", (w, h), SURFACE)
    d = ImageDraw.Draw(img)
    f, fs = font(13), font(10)
    X = lambda yaw: left + (yaw - y0) * s
    Y = lambda pitch: top + (p1 - pitch) * s
    d.text((16, 12), f"Controller-01 executed gaze sequence: {run.name}", fill=INK, font=font(18))
    d.text((16, 38), headline(manifest), fill=INK2, font=f)
    legend(d, 16, 64, [("n", "global action"), ("id", "object at its seed"),
                       ("ring", "first look after a natural reactivation")])
    for v in range(int(y0), int(y1) + 1, 5):
        d.line([X(v), Y(p1), X(v), Y(p0)], fill=GRID)
        d.text((X(v) - 8, Y(p0) + 6), f"{v}°", fill=INK2, font=fs)
    for v in range(int(p0), int(p1) + 1, 5):
        d.line([X(y0), Y(v), X(y1), Y(v)], fill=GRID)
        d.text((left - 34, Y(v) - 6), f"{v}°", fill=INK2, font=fs)
    d.rectangle([X(y0), Y(p1), X(y1), Y(p0)], outline=INK2, width=1)
    d.text((X(0) - 40, Y(p0) + 26), "yaw (deg, +right)", fill=INK2, font=f)
    d.text((8, top - 22), "pitch (deg, +up)", fill=INK2, font=f)
    pts = [(X(a["gaze_deg"][0]), Y(a["gaze_deg"][1])) for a in actions]
    if len(pts) > 1:
        d.line(pts, fill=MUTED, width=1)
    after_react = {a["global_step"] for a in actions if a["scheduler_reason"] == "natural_reactivation"}
    for a, (x, y) in zip(actions, pts):
        marker(d, x, y, a["action_source"], r=4.0)
        if a["global_step"] in after_react:
            d.ellipse([x - 10, y - 10, x + 10, y + 10], outline=INK, width=2)
        d.text((x + 6, y - 2), str(a["global_step"]), fill=INK2, font=fs)
        if a["action_source"] == "oracle_seed":
            d.text((x + 6, y - 14), str(a["target_id"]), fill=INK, font=fs)
    out = run / "controller-gaze-chart.png"
    img.save(out)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path, required=True)
    args = ap.parse_args()
    run = args.run.resolve()
    manifest = json.loads((run / "manifest.json").read_text())
    if not manifest.get("control_complete"):
        raise SystemExit("run is not control_complete")
    doc = json.loads((run / "actions.json").read_text())
    for out in (timeline(run, manifest, doc["actions"], doc["events"]),
                gaze_chart(run, manifest, doc["actions"], doc["events"])):
        print(f"[controller01-plot] wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
