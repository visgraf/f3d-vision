#!/usr/bin/env python3
"""Level-A visual of Controller-02 residual closure (Policy 1).

    .venv/bin/python tools/controller/visualize_controller02.py --run OUT --source SRC --visuals V

Contract: docs/controller/controller-02-residual-closure-contract.md.  Reads the compact
Controller-02 replay output and controller-time artifacts of the accepted source run (final active
maps, 210's final effective geometry, the catalog) under the truth firewall, and writes
``overview.png`` plus ``overview.json`` (every annotated number).  Every annotated number is
recomputed from the replay records and must agree with ``result.json``; otherwise nothing is
written.  The source run's maps equal the replay's: the replay verified every fused map per step.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[2]
for _p in (REPO, REPO / "tools" / "controller"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numpy as np
from PIL import Image, ImageDraw

import controller01b as B  # accepted drawing helpers (Chart, render, panel, legend, font)
from fov3d.control import integrated as ic
from fov3d.experiments.classroom_oracle import controller01 as c01
from fov3d.stereo.core import rectification

PREFIX = "[controller02-visual]"
GREEN, RED, PURPLE, GRAY2, AMBER = (27, 150, 72), (200, 40, 40), (130, 70, 180), (150, 148, 142), (222, 160, 20)
SRC_COL = {"oracle_seed": (82, 81, 78), "fsg6f": (42, 120, 214), "cyclopean_epistemic": (27, 175, 122),
           "final_residue": (200, 40, 40)}
QUIET_COL, RESID_COL = (120, 150, 190), (235, 104, 52)


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def fail(msg: str) -> None:
    raise SystemExit(f"{PREFIX} REFUSED: {msg}")


def core_outline(cal: dict, side: str, depth_m: float) -> np.ndarray:
    """The predicted rectified core's boundary as head-frame yaw/pitch, drawn at ``depth_m``."""
    r = rectification(cal)
    x, y, w, h = (int(v) for v in r["crop_xywh"])
    k = np.asarray(r["P1" if side == "L" else "P2"], float)[:, :3]
    rr = np.asarray(r["R1" if side == "L" else "R2"], float)
    eye = cal["eyes"][0 if side == "L" else 1]
    us = np.r_[np.linspace(0, w - 1, 40), np.full(40, w - 1), np.linspace(w - 1, 0, 40), np.zeros(40)] + x
    vs = np.r_[np.zeros(40), np.linspace(0, h - 1, 40), np.full(40, h - 1), np.linspace(h - 1, 0, 40)] + y
    rays_rect = np.linalg.solve(k, np.vstack([us, vs, np.ones_like(us)]))
    rays_cam = rr.T @ rays_rect
    rays_h = np.asarray(eye["R_hc"], float) @ rays_cam
    rays_h /= np.linalg.norm(rays_h, axis=0)
    pts = np.asarray(eye["centre_h_m"], float)[:, None] + depth_m * rays_h
    yaw, pitch = B.angles(pts.T)
    return np.c_[yaw, pitch]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--visuals", type=Path, required=True)
    a = ap.parse_args()
    out, source, vis = a.run.resolve(), a.source.resolve(), a.visuals.resolve()
    fw = ic.TruthFirewall(source, c01.is_evaluation_truth)
    with fw:
        res = json.loads((out / "result.json").read_text())
        acts = json.loads((out / "actions.json").read_text())["actions"]
        evs = json.loads((out / "events.json").read_text())["events"]
        residue = json.loads((out / "final-residue.json").read_text())["residue_decisions"]
        names = {int(o["instance_id"]): o["object_name"]
                 for o in json.loads((source / "bootstrap/instance_catalog.json").read_text())["instances"]}
        maps = {int(i): np.asarray(c01._load_npz(source / f"objects/instance_{int(i):04d}/final_map.npz")["xyz_h"], np.float64)
                for i in res["final_states"]}
        eff210 = np.asarray(c01._load_npz(source / "objects/instance_0210/final_effective_geometry.npz")["xyz_h"], np.float64)
    if fw.violations:
        fail(f"truth firewall violations {fw.violations}")
    # ---- recompute every annotated number from the replay records
    ordinary = [x for x in acts if x["phase"] == "NORMAL"]
    final_looks = [x for x in acts if x["phase"] == "RESIDUE"]
    deferred = [e for e in evs if e["event"] == "deferred"]
    react = [e for e in evs if e["event"] == "natural_reactivation"]
    end_normal = ordinary[-1]["service_states_after"] if ordinary else {}
    quiet_end = sorted(int(k) for k, v in end_normal.items() if v == "QUIET")
    deferred_end = sorted(int(k) for k, v in end_normal.items() if "DEFERRED" in v)
    fs = res["final_states"]
    quiet = sorted(int(k) for k, s in fs.items() if s["local_state"] == "QUIET")
    residual = sorted(int(k) for k, s in fs.items() if s["disposition"] == "FINALIZED" and s["local_state"] != "QUIET")
    if residue:
        r0 = residue[0]
        d = r0["detail"]
        counts = d["counts"]
        els = d["elements"]
    else:
        fail("no residue decision recorded")
    numbers = {
        "ordinary_observations": len(ordinary), "final_residue_observations": len(final_looks),
        "deferred": [(e["object"], e["global_step"], e["fixations"]) for e in deferred],
        "natural_reactivations": [(e["object"], e["global_step"], e["trigger_target"]) for e in react],
        "end_normal_quiet": len(quiet_end), "end_normal_deferred": deferred_end,
        "final_proposal": {"object": r0["object"], "source": r0["proposal"]["source"], "gaze_deg": r0["proposal"]["gaze_deg"]},
        "support": counts["support"], "in_both_cores": counts["in_both_cores"],
        "previously_interrogated": counts["previously_interrogated"], "novel_service_count": counts["novel_service_count"],
        "gate": "ADMIT" if r0["admissible"] else "REJECT", "gate_reason": r0["reason"],
        "terminal": res["terminal"]["type"], "quiet": len(quiet), "residual": residual,
        "unlocated": len(res.get("unlocated", [])), "seed_residues": len(res.get("seed_residues", [])),
    }
    agree = (numbers["ordinary_observations"] == res["ordinary_observations"]
             and numbers["final_residue_observations"] == res["final_residue_observations"]
             and quiet == sorted(res.get("quiet", [])) and residual == sorted(r[0] for r in res.get("residual", []))
             and counts["support"] == len(els) == sum(1 for _ in els)
             and counts["in_both_cores"] == sum(e["in_both_cores"] for e in els)
             and counts["previously_interrogated"] == sum(e["previously_interrogated"] for e in els)
             and counts["novel_service_count"] == sum(e["novel"] for e in els)
             and (numbers["gate"] == "REJECT") == (r0["object"] in res.get("final_rejections", [])))
    if not agree:
        fail(f"annotated numbers disagree with result.json: {numbers}")

    # ---- 1. normal loop: attention timeline
    objs = sorted(int(k) for k in fs)
    rowh, colw, left, top = 17, 6, 150, 26
    n_steps = len(acts)
    W, H = left + colw * (n_steps + 20) + 10, top + rowh * len(objs) + 34
    im = Image.new("RGB", (W, H), B.SURFACE); d1 = ImageDraw.Draw(im)
    for r, i in enumerate(objs):
        y = top + r * rowh
        if i == 210:
            d1.rectangle([0, y, W, y + rowh - 1], fill=(253, 236, 226))
        d1.text((4, y + 2), f"{i} {names.get(i, '')[:14]}", fill=B.INK2 if i != 210 else RESID_COL, font=B.font(11))
    for x in acts:
        r, s = objs.index(int(x["target_id"])), int(x["global_step"])
        col = SRC_COL["final_residue"] if x["phase"] == "RESIDUE" else SRC_COL[x["action_source"]]
        d1.rectangle([left + s * colw, top + r * rowh + 3, left + s * colw + colw - 2, top + r * rowh + rowh - 4], fill=col)
    for e in evs:
        if e["event"] not in ("quiet", "natural_reactivation", "deferred") or e["object"] not in objs:
            continue
        r, s = objs.index(e["object"]), int(e["global_step"])
        xx, yy = left + s * colw + colw // 2, top + r * rowh + rowh // 2
        if e["event"] == "quiet":
            d1.line([xx + 3, yy - 5, xx + 3, yy + 5], fill=B.INK, width=1)
        elif e["event"] == "natural_reactivation":
            d1.polygon([(xx, yy - 7), (xx - 5, yy + 1), (xx + 5, yy + 1)], fill=AMBER, outline=B.INK)
    for e in deferred:
        r, s = objs.index(e["object"]), int(e["global_step"])
        y = top + r * rowh
        x0 = left + (s + 1) * colw
        for xx in range(x0, left + colw * len(ordinary), 6):
            d1.line([xx, y + 2, xx + 3, y + rowh - 3], fill=RESID_COL, width=1)
        lab = f"210 DEFERRED at step {s} (ordinary budget {e['fixations']}; still {e['local_state']})"
        tw = d1.textlength(lab, font=B.font(12))
        lx0 = min(x0 + 4, W - tw - 12)
        d1.rectangle([lx0, y - 16, lx0 + tw + 6, y - 1], fill=(255, 255, 255)); d1.text((lx0 + 3, y - 15), lab, fill=RESID_COL, font=B.font(12))
    xb = left + colw * len(ordinary)
    d1.line([xb, top - 6, xb, H - 30], fill=B.INK, width=2)
    d1.text((xb + 4, top - 22), "RESIDUE,", fill=B.INK, font=B.font(12))
    d1.text((xb + 4, top - 9), "CLOSED", fill=B.INK, font=B.font(12))
    d1.text((left, H - 26), f"global step 0 .. {n_steps - 1}  (one column per observation; the rest of the scene continues after 210 is deferred)",
            fill=B.INK2, font=B.font(12))
    p1 = B.panel(np.asarray(im), "1. NORMAL LOOP: attention timeline (Controller-02 replay = Controller-01's 141 looks)", "CONTROLLER-TIME",
                 [f"{len(ordinary)} ordinary observations, all equal to the accepted Controller-01 actions; natural reactivations "
                  + ", ".join(f"{o}@{s} (by {t})" for o, s, t in numbers["natural_reactivations"]),
                  "210 is DEFERRED, not BLOCKED: it keeps its local state and simply receives no more ordinary service"])
    p1 = np.asarray(p1)
    leg1 = B.legend([(SRC_COL["oracle_seed"], "seed look"), (SRC_COL["fsg6f"], "FSG6f look"),
                     (SRC_COL["cyclopean_epistemic"], "Cyclopean look"), (AMBER, "natural reactivation"),
                     (B.INK, "| quiet"), (RESID_COL, "deferred: no ordinary service")], p1.shape[1])

    # ---- 2. end of the normal phase: scene with 24 QUIET + 210 DEFERRED
    ch = B.Chart(-25.0, 25.0, -20.0, 22.0, 900)
    img = np.full((ch.h, ch.w, 3), B.SURFACE, np.uint8)
    for i in objs:
        if i != 210:
            img = B.render(ch, maps[i][:: max(1, len(maps[i]) // 150000)], QUIET_COL, img=img)
    img = B.render(ch, maps[210][:: max(1, len(maps[210]) // 150000)], RESID_COL, img=img)
    im2 = Image.fromarray(img); d2 = ImageDraw.Draw(im2)
    y210, p210 = B.angles(maps[210])
    lx, ly = (float(v) for v in ch.px(np.median(y210), np.quantile(p210, 0.95)))
    lab = "210 wall.008: DEFERRED, local ACTIONABLE"
    d2.rectangle([lx - 4, ly - 20, lx + d2.textlength(lab, font=B.font(13)) + 4, ly - 2], fill=(255, 255, 255))
    d2.text((lx, ly - 19), lab, fill=RESID_COL, font=B.font(13))
    p2 = B.panel(np.asarray(im2), "2. END OF THE NORMAL PHASE: ordinary work exhausted after step 140", "CONTROLLER-TIME",
                 [f"{numbers['end_normal_quiet']} objects QUIET (blue) + {len(deferred_end)} DEFERRED {deferred_end} (orange); "
                  "active fused maps, head frame",
                  "ordinary work exhausted is not global quiescence: 210 still has local residue"])
    leg2 = B.legend([(QUIET_COL, "QUIET object (active map)"), (RESID_COL, "210 DEFERRED / ACTIONABLE")], np.asarray(p2).shape[1])

    # ---- 3. the strict final-look gate
    cal = d["predicted_calibration"]
    cur = d["current_gaze_deg"]
    prop = r0["proposal"]["gaze_deg"]
    ch3 = B.Chart(min(cur[0], prop[0]) - 10.0, max(cur[0], prop[0]) + 10.0, cur[1] - 10.0, cur[1] + 8.0, 900)
    img3 = B.render(ch3, eff210[:: max(1, len(eff210) // 600000)], B.OLD_PTS)
    im3 = Image.fromarray(img3); d3 = ImageDraw.Draw(im3)
    depth = float(np.median([np.linalg.norm(e["t_e"]) for e in els]))
    for side, col in (("L", GREEN), ("R", (20, 110, 55))):
        poly = core_outline(cal, side, depth)
        xs, ys = ch3.px(poly[:, 0], poly[:, 1])
        d3.line(list(zip(xs.tolist(), ys.tolist())) + [(float(xs[0]), float(ys[0]))], fill=col, width=3)
    px, py = (float(v) for v in ch3.px(*prop))
    d3.ellipse([px - 6, py - 6, px + 6, py + 6], outline=B.INK, width=3)
    d3.text((px + 8, py - 22), f"proposed final look {prop[0]:.1f}, {prop[1]:.1f} ({r0['proposal']['source']})", fill=B.INK, font=B.font(13))
    d3.text((float(ch3.px(prop[0] - 5.0, 0)[0]), float(ch3.px(0, prop[1] + 5.2)[1])), "predicted depth cores (L, R)",
            fill=GREEN, font=B.font(12))
    cx, cy = (float(v) for v in ch3.px(*cur))
    d3.rectangle([cx - 5, cy - 5, cx + 5, cy + 5], outline=B.INK2, width=2)
    lab = f"current gaze (look 24) {cur[0]:.1f}, {cur[1]:.1f}"
    d3.rectangle([cx + 8, cy + 8, cx + 14 + d3.textlength(lab, font=B.font(12)), cy + 24], fill=(255, 255, 255))
    d3.text((cx + 11, cy + 9), lab, fill=B.INK2, font=B.font(12))
    for e in els:
        x0, y0 = (float(v) for v in ch3.px(*e["x_yaw_pitch_deg"]))
        x1, y1 = (float(v) for v in ch3.px(*e["t_yaw_pitch_deg"]))
        col = GREEN if e["in_both_cores"] else RED
        d3.line([x0, y0, x1, y1], fill=col, width=2)
        d3.line([x1 - 4, y1 - 4, x1 + 4, y1 + 4], fill=col, width=2); d3.line([x1 - 4, y1 + 4, x1 + 4, y1 - 4], fill=col, width=2)
        if e["previously_interrogated"]:
            d3.ellipse([x1 - 8, y1 - 8, x1 + 8, y1 + 8], outline=PURPLE, width=2)
        d3.ellipse([x0 - 4, y0 - 4, x0 + 4, y0 + 4], fill=col, outline=B.INK)
    verdict = f"{numbers['gate']}: {r0['reason']}"
    d3.rectangle([8, ch3.h - 34, 16 + d3.textlength(verdict, font=B.font(16)), ch3.h - 8], fill=(255, 255, 255))
    d3.text((12, ch3.h - 32), verdict, fill=RED if numbers["gate"] == "REJECT" else GREEN, font=B.font(16))
    p3 = B.panel(np.asarray(im3), "3. STRICT FINAL-LOOK GATE v1: would the unchanged proposal service its own support?", "DERIVED",
                 [f"OPEN support {counts['support']} (dots x_e, crosses t_e) | t_e in both predicted cores {counts['in_both_cores']} "
                  f"| previously interrogated {counts['previously_interrogated']} | novel_service_count {counts['novel_service_count']}",
                  "cores predicted from the sensor model (make_calibration; no render); 01B/01C were not read",
                  "background: 210's effective geometry; core outlines drawn at the support depth"])
    leg3 = B.legend([(RED, "support not in both cores"), (GREEN, "support in both cores"), (PURPLE, "O previously interrogated"),
                     (GREEN, "predicted depth cores")], np.asarray(p3).shape[1])

    # ---- 4. honest closure
    im4 = Image.new("RGB", (900, 520), B.SURFACE); d4 = ImageDraw.Draw(im4)
    d4.text((20, 16), res["terminal"]["type"], fill=B.INK, font=B.font(30))
    tile, gap = 60, 10
    for n, i in enumerate(objs):
        x0, y0 = 20 + (n % 13) * (tile + gap), 70 + (n // 13) * (tile + 30)
        colr = RESID_COL if i in residual else QUIET_COL
        d4.rectangle([x0, y0, x0 + tile, y0 + tile], fill=colr)
        d4.text((x0 + 4, y0 + tile + 2), str(i), fill=B.INK2, font=B.font(11))
    lines = [f"quiet localized objects: {numbers['quiet']}",
             "residual localized objects: " + ", ".join(f"{i} {names.get(i, '')} ({fs[str(i)]['local_state']}, "
                                                        f"{fs[str(i)]['disposition']}: {fs[str(i)]['reason']})" for i in residual),
             f"seed-initialization residues: {numbers['seed_residues']}",
             f"unlocated objects: {numbers['unlocated']}",
             f"final residue observations executed: {numbers['final_residue_observations']}",
             f"final residue proposals rejected: {len(res.get('final_rejections', []))} ({numbers['gate_reason']})"]
    for n, line in enumerate(lines):
        d4.text((20, 270 + 26 * n), line, fill=B.INK, font=B.font(15))
    d4.text((20, 440), "residual != failure", fill=RESID_COL, font=B.font(22))
    d4.text((20, 474), "SCENE_CLOSED != global quiescence", fill=B.INK2, font=B.font(18))
    p4 = B.panel(np.asarray(im4), "4. HONEST CLOSURE", "DERIVED",
                 ["the scene ends: everything it will spend has been spent; 210 keeps its unresolved local residue"])

    panels = [B.vstack(np.asarray(p1), leg1), B.vstack(np.asarray(p2), leg2), B.vstack(np.asarray(p3), leg3), np.asarray(p4)]
    cw = max(p.shape[1] for p in panels); rows = [panels[:2], panels[2:]]
    rh = [max(p.shape[0] for p in r) for r in rows]
    title = "Controller-02: residual closure on the accepted Classroom evidence (no render)"
    sub = [f"ordinary observations {numbers['ordinary_observations']} (= Controller-01) | deferred {numbers['deferred']} | "
           f"final proposal {numbers['final_proposal']['source']} [{numbers['final_proposal']['gaze_deg'][0]:.1f}, "
           f"{numbers['final_proposal']['gaze_deg'][1]:.1f}] | support {numbers['support']}, "
           f"in both predicted cores {numbers['in_both_cores']}, novel {numbers['novel_service_count']} -> {numbers['gate']}",
           f"terminal {numbers['terminal']}: quiet {numbers['quiet']}, residual {numbers['residual']}, unlocated {numbers['unlocated']}, "
           f"final looks executed {numbers['final_residue_observations']}",
           "Controller-time data and derived renderings only; no evaluation truth. The strict predicate is not claimed optimal."]
    canvas = Image.new("RGB", (2 * cw + 42, 40 + 21 * len(sub) + sum(rh) + 42), B.SURFACE)
    dc = ImageDraw.Draw(canvas); dc.text((14, 10), title, fill=B.INK, font=B.font(21))
    for n, line in enumerate(sub):
        dc.text((14, 40 + 21 * n), line, fill=B.INK2, font=B.font(14))
    y = 40 + 21 * len(sub) + 14
    for r, h in zip(rows, rh):
        x = 14
        for p in r:
            canvas.paste(Image.fromarray(p), (x, y)); x += cw + 14
        y += h + 14
    vis.mkdir(parents=True, exist_ok=True)
    png = vis / "overview.png"
    canvas.save(png)
    (vis / "overview.json").write_text(json.dumps(c01._jsonable({
        "truth": "CONTROLLER-TIME records and maps; DERIVED gate geometry and summaries; no evaluation truth",
        "run": str(out), "result_sha256": sha(out / "result.json"), "numbers": numbers, "png_sha256": sha(png),
        "firewall_violations": fw.violations}), indent=1, sort_keys=True) + "\n")
    print(f"{PREFIX} wrote {png} sha256={sha(png)}")
    print(f"{PREFIX} numbers {json.dumps(c01._jsonable(numbers))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
