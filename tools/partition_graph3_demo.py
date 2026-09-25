#!/usr/bin/env python3
"""Generate the Partition-Graph Phase 3 joint-partition/corridor demo."""
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

# Chart area = 1.25x the 501x401 chart (626x502) plus 58 px of title/footer: nearest
# upsampling keeps every chart row and column, so one-cell corridors cannot be dropped.
PANEL_W, PANEL_H = 626, 560


def _id_color(iid: int) -> tuple[int, int, int]:
    x = int(iid)
    return ((53 * x + 70) % 190 + 35, (97 * x + 20) % 190 + 35, (151 * x + 10) % 190 + 35)


def _owner_rgb(owner: np.ndarray, current: int) -> np.ndarray:
    out = np.full(owner.shape + (3,), 235, np.uint8)
    for iid in np.unique(owner):
        iid = int(iid)
        if iid <= 0:
            continue
        out[owner == iid] = _id_color(iid)
    # Current target gets a constant high-contrast display color.
    out[owner == int(current)] = (40, 210, 245)
    return out


def _component_rgb(region_code: np.ndarray, owner: np.ndarray, current: int, corridors: list[dict]) -> np.ndarray:
    out = np.full(region_code.shape + (3,), 224, np.uint8)
    target = owner == int(current)
    codes = sorted(int(v) for v in np.unique(region_code[target]))
    for k, code in enumerate(codes, start=1):
        if code <= 0:
            continue
        out[region_code == code] = _id_color(1000 + 17 * k)
    other = (owner > 0) & ~target
    out[other] = (150, 150, 150)
    # All relations are drawn; there is no silent text-list truncation.
    for rel in corridors:
        pts = np.asarray(rel.get("corridor_yx", []), np.int32)
        if len(pts):
            out[pts[:, 0], pts[:, 1]] = (25, 25, 240)
    return out


def _seen_rgb(seen: np.ndarray) -> np.ndarray:
    out = np.zeros(seen.shape + (3,), np.uint8)
    out[:] = (35, 35, 35)
    out[np.asarray(seen, bool)] = (80, 200, 100)
    return out


def _panel(img: np.ndarray, title: str, footer: str = "") -> np.ndarray:
    # Chart row 0 is minimum pitch. Flip for a conventional view: positive pitch up.
    img = np.flipud(img)
    img = cv2.resize(img, (PANEL_W, PANEL_H - 58), interpolation=cv2.INTER_NEAREST)
    out = np.full((PANEL_H, PANEL_W, 3), 247, np.uint8)
    out[36:36 + img.shape[0]] = img
    cv2.putText(out, title, (12, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (20, 20, 20), 1, cv2.LINE_AA)
    if footer:
        cv2.putText(out, footer[:92], (12, PANEL_H - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (40, 40, 40), 1, cv2.LINE_AA)
    return out


def _text_panel(lines: list[str], title: str) -> np.ndarray:
    out = np.full((PANEL_H, PANEL_W, 3), 250, np.uint8)
    cv2.putText(out, title, (12, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (20, 20, 20), 1, cv2.LINE_AA)
    y = 56
    for line in lines:
        if y > PANEL_H - 18:
            break
        cv2.putText(out, line[:88], (14, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (30, 30, 30), 1, cv2.LINE_AA)
        y += 20
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("lift_dir")
    ap.add_argument("out_dir", nargs="?")
    args = ap.parse_args()
    lift = Path(args.lift_dir)
    out = Path(args.out_dir or (lift / "demo"))
    out.mkdir(parents=True, exist_ok=True)
    summary = json.loads((lift / "summary.json").read_text(encoding="utf-8"))

    frames: list[Path] = []
    frame_meta: list[tuple[tuple[int, int, int, int], int, Path]] = []
    for s in summary["global_states"]:
        if not s.get("map_present"):
            continue
        gi = int(s["global_index"])
        iid = int(s["instance_id"])
        step = int(s["local_step"])
        d = lift / "states" / f"global_{gi:03d}"
        with np.load(d / "state.npz", allow_pickle=False) as z:
            owner = np.array(z["owner_instance"])
            rc = np.array(z["region_code"])
            seen = np.array(z["current_target_seen_any"], bool)
        corridors = json.loads((d / "corridors.json").read_text(encoding="utf-8"))

        p1 = _panel(
            _owner_rgb(owner, iid),
            f"joint frontmost partition: global {gi}, target {iid}, fix {step}",
            "white=BASE | yellow=current target | other colors=already reconstructed objects",
        )
        p2 = _panel(
            _component_rgb(rc, owner, iid, corridors),
            "current-target components + every local gap corridor",
            "component colors=current target | gray=other objects | red=local corridor",
        )
        p3 = _panel(
            _seen_rgb(seen),
            "exact historical controller seen_any evidence",
            "dark=UNSEEN | green=SEEN supported rectified core (not raw tangent quad)",
        )

        gaps = [float(r["endpoint_gap_deg"]) for r in corridors]
        crossing = sum(int(r["other_object_cells"] > 0) for r in corridors)
        unseen = sum(int(r["unseen_cells"] > 0) for r in corridors)
        bd = s["boundary_diagnostics"]
        lines = [
            f"objects present: {s['objects_present']}",
            f"scene object regions: {s['object_regions']}",
            f"BASE regions (4-connected): {s['base_regions']}",
            f"object-object boundaries: {s['object_object_boundaries']}",
            f"object-BASE boundaries: {s['object_base_boundaries']}",
            f"current target components: {s['current_target_components']}",
            f"all component pairs/corridors: {len(corridors)}",
            f"corridors crossing mapped other object: {crossing}",
            f"corridors containing unseen cells: {unseen}",
            f"gap deg min/max: {min(gaps):.2f}/{max(gaps):.2f}" if gaps else "gap deg min/max: -/-",
            "",
            f"raster interface edges: {bd['raster_interface_edges']}",
            f"encoded interface edges: {bd['encoded_interface_edges']}",
            f"unencoded: {bd['unencoded_interface_edges']}",
        ]
        p4 = _text_panel(lines, "joint dual + local relation summary (descriptive only)")
        frame = np.vstack((np.hstack((p1, p2)), np.hstack((p3, p4))))
        fn = out / f"frame_{len(frames):04d}.png"
        cv2.imwrite(str(fn), frame)
        frames.append(fn)
        score = (
            int(len(corridors) > 0),
            int(s["object_object_boundaries"]),
            int(len(corridors)),
            int(s["object_regions"]),
        )
        frame_meta.append((score, iid, fn))

    if frames:
        first = cv2.imread(str(frames[0]))
        h, w = first.shape[:2]
        vw = cv2.VideoWriter(str(out / "partition-graph-3-demo.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), 4.0, (w, h))
        if vw.isOpened():
            for f in frames:
                vw.write(cv2.imread(str(f)))
            vw.release()

        # Best-scoring frame per target first, so the overview shows six different targets
        # rather than consecutive near-identical states of one target.
        best: dict[int, tuple[tuple[int, int, int, int], Path]] = {}
        for score, iid, fn in frame_meta:
            if iid not in best or score > best[iid][0]:
                best[iid] = (score, fn)
        picks = [p for _score, p in sorted(best.values(), reverse=True)[:6]]
        if frames[-1] not in picks:
            picks = (picks[:5] + [frames[-1]]) if len(picks) >= 5 else picks + [frames[-1]]
        thumbs = [cv2.resize(cv2.imread(str(p)), (w // 2, h // 2), interpolation=cv2.INTER_AREA) for p in picks]
        while thumbs and len(thumbs) % 2:
            thumbs.append(np.full_like(thumbs[0], 255))
        if thumbs:
            ov = np.vstack([np.hstack(thumbs[i:i + 2]) for i in range(0, len(thumbs), 2)])
            cv2.imwrite(str(out / "overview.png"), ov)

    ev = summary["controller_seen_any_validation"]
    (out / "Demo.md").write_text(
        "# Partition-Graph Phase 3 demo\n\n"
        "Post-hoc visualization only. No panel participated in the historical gaze policy and no dense evaluation truth is read.\n\n"
        "Panels show the joint frontmost spherical partition, all current-target local gap corridors, the exact replayed historical `seen_any` evidence raster, and aggregate dual/topology measurements. Raster orientation is conventional: positive pitch is up.\n\n"
        f"Frames: {len(frames)}. Controller-evidence audit checkpoints: {ev['checks']}; mismatches: {ev['mismatches']}.\n\n"
        "All corridor records are in each state's `corridors.json`; the visual panel draws every corridor and does not silently truncate a relation list.\n\n"
        f"Regenerate with:\n\n```bash\n./.venv/bin/python tools/partition_graph3_demo.py {lift} {out}\n```\n",
        encoding="utf-8",
    )
    print(f"[partition-graph3-demo] wrote {len(frames)} frames to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
