#!/usr/bin/env python3
"""Generate the Partition-Graph Phase 4 typed-relation/evidence demo."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fov3d.experiments.classroom_partition.relations import EVIDENCE_CLASS_NAMES

PANEL_W, PANEL_H = 626, 560


def _id_color(iid: int) -> tuple[int, int, int]:
    x = int(iid)
    return ((53 * x + 70) % 190 + 35, (97 * x + 20) % 190 + 35, (151 * x + 10) % 190 + 35)


def _owner_rgb(owner: np.ndarray, current: int) -> np.ndarray:
    out = np.full(owner.shape + (3,), 235, np.uint8)
    for iid in np.unique(owner):
        iid = int(iid)
        if iid > 0:
            out[owner == iid] = _id_color(iid)
    out[owner == int(current)] = (40, 210, 245)
    return out


def _relation_rgb(region_code: np.ndarray, owner: np.ndarray, current: int, relations: list[dict]) -> np.ndarray:
    out = np.full(region_code.shape + (3,), 224, np.uint8)
    target = owner == int(current)
    codes = sorted(int(v) for v in np.unique(region_code[target]) if int(v) > 0)
    for k, code in enumerate(codes, start=1):
        out[region_code == code] = _id_color(1000 + 17 * k)
    out[(owner > 0) & ~target] = (150, 150, 150)
    for rel in relations:
        pts = np.asarray(rel.get("corridor_yx", []), np.int32)
        if not len(pts):
            continue
        # BGR: magenta = ownership cut, red = genuine own-support gap.
        color = (220, 40, 220) if rel.get("relation_origin") == "ownership_cut" else (30, 30, 235)
        out[pts[:, 0], pts[:, 1]] = color
    return out


def _evidence_rgb(codes: np.ndarray) -> np.ndarray:
    # BGR palette; all six states intentionally distinct.
    palette = np.array([
        [35, 35, 35],      # UNSEEN
        [185, 185, 185],   # SEEN_NO_LEFT_ID_EVIDENCE
        [235, 170, 60],    # LEFT_NONTARGET_ONLY
        [60, 215, 230],    # LEFT_TARGET_NO_DEPTH
        [210, 80, 200],    # LEFT_MIXED_NO_DEPTH
        [75, 200, 80],     # TARGET_DEPTH_VALID
    ], np.uint8)
    a = np.asarray(codes, np.int32)
    return palette[np.clip(a, 0, len(palette) - 1)]


def _panel(img: np.ndarray, title: str, footer: str = "") -> np.ndarray:
    # row 0 is minimum pitch; flip so positive pitch is up.
    img = np.flipud(img)
    img = cv2.resize(img, (PANEL_W, PANEL_H - 58), interpolation=cv2.INTER_NEAREST)
    out = np.full((PANEL_H, PANEL_W, 3), 247, np.uint8)
    out[36:36 + img.shape[0]] = img
    cv2.putText(out, title, (12, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (20, 20, 20), 1, cv2.LINE_AA)
    if footer:
        # Shrink the footer font until the whole key fits the panel width (never truncate a key).
        scale = 0.40
        while scale > 0.30 and cv2.getTextSize(footer, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)[0][0] > PANEL_W - 20:
            scale -= 0.01
        cv2.putText(out, footer, (10, PANEL_H - 8), cv2.FONT_HERSHEY_SIMPLEX, scale, (40, 40, 40), 1, cv2.LINE_AA)
    return out


def _text_panel(lines: list[str], title: str) -> np.ndarray:
    out = np.full((PANEL_H, PANEL_W, 3), 250, np.uint8)
    cv2.putText(out, title, (12, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (20, 20, 20), 1, cv2.LINE_AA)
    y = 54
    for line in lines:
        if y > PANEL_H - 16:
            break
        cv2.putText(out, line[:88], (14, y), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (30, 30, 30), 1, cv2.LINE_AA)
        y += 19
    return out


def _relation_lines(relations: list[dict]) -> list[str]:
    cuts = [r for r in relations if r.get("relation_origin") == "ownership_cut"]
    gaps = [r for r in relations if r.get("relation_origin") == "own_support_gap"]
    lines = [
        f"relations: {len(relations)}  ownership_cut={len(cuts)}  own_support_gap={len(gaps)}",
        "magenta=ownership cut | red=own-support gap",
        "",
    ]
    # Show strongest/longest few relations; all remain drawn and all records remain JSON.
    ranked = sorted(relations, key=lambda r: float(r.get("endpoint_gap_deg", 0.0)), reverse=True)
    for r in ranked[:8]:
        ec = r.get("evidence_class_counts", {})
        margin = r.get("ownership_margin", {})
        m = margin.get("median_m")
        mtxt = "-" if m is None else f"{1000.0*float(m):.1f}mm"
        lines.append(
            f"{r.get('relation_origin','?')[:13]} gap={float(r.get('endpoint_gap_deg',0)):.2f}deg "
            f"B/O={r.get('base_cells',0)}/{r.get('other_object_cells',0)} "
            f"depth={ec.get('TARGET_DEPTH_VALID',0)} margin={mtxt}"
        )
    lines += ["", "No policy/occlusion verdict is made in Phase 4."]
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("lift_dir")
    ap.add_argument("analysis_dir")
    ap.add_argument("out_dir", nargs="?")
    args = ap.parse_args()
    lift = Path(args.lift_dir)
    analysis = Path(args.analysis_dir)
    out = Path(args.out_dir or (analysis / "demo"))
    out.mkdir(parents=True, exist_ok=True)
    ls = json.loads((lift / "summary.json").read_text(encoding="utf-8"))
    ps = json.loads((analysis / "summary.json").read_text(encoding="utf-8"))

    frames: list[Path] = []
    per_target: dict[int, tuple[tuple[int, int, float], Path]] = {}
    for s in ls["global_states"]:
        if not s.get("map_present"):
            continue
        gi = int(s["global_index"]); iid = int(s["instance_id"]); step = int(s["local_step"])
        sd = lift / "states" / f"global_{gi:03d}"
        ad = analysis / "states" / f"global_{gi:03d}"
        with np.load(sd / "state.npz", allow_pickle=False) as z:
            owner = np.array(z["owner_instance"])
            rc = np.array(z["region_code"])
        with np.load(ad / "evidence.npz", allow_pickle=False) as z:
            ev = np.array(z["evidence_class"])
        rels = json.loads((ad / "relations.json").read_text(encoding="utf-8"))

        p1 = _panel(_owner_rgb(owner, iid), f"joint partition: global {gi}, target {iid}, fix {step}",
                    "white=BASE | yellow=current target | colors=already reconstructed objects")
        p2 = _panel(_relation_rgb(rc, owner, iid, rels), "typed disconnected-component relations",
                    "magenta=ownership_cut | red=own_support_gap | all corridors drawn")
        # Colour names follow the BGR palette in _evidence_rgb as displayed (RGB).
        p3 = _panel(_evidence_rgb(ev), "fine controller-time evidence overlay",
                    "dark UNSEEN | gray seen,no L-id | blue L-nontarget | yellow L-target no-depth | "
                    "purple L-mixed | green depth-valid")
        p4 = _text_panel(_relation_lines(rels), "local relation diagnostics (descriptive only)")
        frame = np.vstack((np.hstack((p1, p2)), np.hstack((p3, p4))))
        fn = out / f"frame_{len(frames):04d}.png"
        if not cv2.imwrite(str(fn), frame):
            raise RuntimeError(f"could not write {fn}")
        frames.append(fn)
        score = (len(rels), sum(r.get("relation_origin") == "own_support_gap" for r in rels),
                 max([float(r.get("endpoint_gap_deg", 0.0)) for r in rels] or [0.0]))
        if iid not in per_target or score > per_target[iid][0]:
            per_target[iid] = (score, fn)

    if frames:
        first = cv2.imread(str(frames[0])); hh, ww = first.shape[:2]
        vw = cv2.VideoWriter(str(out / "partition-graph-4-demo.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), 4.0, (ww, hh))
        if not vw.isOpened():
            raise RuntimeError("could not open MP4 writer")
        for f in frames:
            vw.write(cv2.imread(str(f)))
        vw.release()

        # One representative frame per target, arranged 5 columns.
        picks = [p for _score, p in sorted(per_target.values(), key=lambda x: str(x[1]))]
        thumbs = [cv2.resize(cv2.imread(str(p)), (ww // 4, hh // 4), interpolation=cv2.INTER_AREA) for p in picks]
        if thumbs:
            cols = 5
            blank = np.full_like(thumbs[0], 255)
            while len(thumbs) % cols:
                thumbs.append(blank.copy())
            ov = np.vstack([np.hstack(thumbs[i:i + cols]) for i in range(0, len(thumbs), cols)])
            cv2.imwrite(str(out / "overview.png"), ov)

    dv = ps["target_depth_valid_validation"]
    sn = ps["controller_seen_any_validation"]
    (out / "Demo.md").write_text(
        "# Partition-Graph Phase 4 demo\n\n"
        "Retrospective analysis only. No frame or relation participated in the historical gaze policy. "
        "No dense evaluation truth, raw oracle observation, EXR, or Blender scene is read.\n\n"
        "Panels show the joint frontmost partition, typed local corridors, the finer controller-time "
        "evidence replay, and relation diagnostics. Positive pitch is up. Every corridor is drawn; the "
        "text panel may summarize only a few because complete records remain in `relations.json`.\n\n"
        f"Frames: {len(frames)}. NEVER_OBSERVED checks: {sn.get('checks')}, mismatches: {sn.get('mismatches')}. "
        f"TARGET_DEPTH_VALID checks: {dv.get('checks')}, mismatches: {dv.get('mismatches')}.\n\n"
        f"Evidence classes: {', '.join(EVIDENCE_CLASS_NAMES)}.\n\n"
        "## Keys and semantics\n\n"
        "Relation panel: magenta = `ownership_cut` (both corridor endpoints lie in one connected "
        "component of the target's own support; a nearer reconstructed object won the cells between); "
        "red = `own_support_gap` (endpoints lie in different components of the target's own support). "
        "Where corridors of different origin overlap, the later-drawn one covers the earlier.\n\n"
        "Evidence panel (one class per cell, precedence top to bottom; the boolean masks are kept "
        "separately in `evidence.npz`):\n\n"
        "| colour | class | meaning |\n|---|---|---|\n"
        "| green | `TARGET_DEPTH_VALID` | a supported left-core target pixel with valid oracle stereo depth "
        "(exact replay of the historical mask) |\n"
        "| purple | `LEFT_MIXED_NO_DEPTH` | left eye saw both the target and a non-target instance, no valid target depth |\n"
        "| yellow | `LEFT_TARGET_NO_DEPTH` | left eye saw only the target, no valid target depth |\n"
        "| blue | `LEFT_NONTARGET_ONLY` | left eye saw only non-target instance ids |\n"
        "| gray | `SEEN_NO_LEFT_ID_EVIDENCE` | seen by the two-eye `seen_any` replay but no left-eye id evidence |\n"
        "| dark | `UNSEEN` | never in a supported rectified core of this target's looks |\n\n"
        "The left-derived masks are left-eye subsets, not the historical two-eye `seen_target` / "
        "`seen_nontarget` masks. Instance ids are Oracle-1's inherited oracle labels. Evidence is marked "
        "along eye rays (as the historical epistemic module did), while the partition projects maps from "
        "the head origin, so evidence can sit a few cells in yaw off the partition (eye offset 31.5 mm). "
        "In the diagnostics panel, `depth=` counts `TARGET_DEPTH_VALID` cells over the whole corridor "
        "interior, including the target's own other components.\n\n"
        f"Regenerate with:\n\n```bash\n./.venv/bin/python tools/partition_graph4_demo.py {lift} {analysis} {out}\n```\n",
        encoding="utf-8",
    )
    print(f"[partition-graph4-demo] wrote {len(frames)} frames to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
