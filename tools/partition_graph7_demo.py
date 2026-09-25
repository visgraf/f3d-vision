#!/usr/bin/env python3
"""Generate the Phase-7 prefix local-vs-global benchmark demo (evaluation-side)."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import sys
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from fov3d.experiments.classroom_partition.benchmark import REGION_KIND_BY_CODE

PANEL_W, PANEL_H = 626, 560


def _region_rgb(class_code: np.ndarray, region_code: np.ndarray) -> np.ndarray:
    cc = np.asarray(class_code, np.uint8)
    rc = np.asarray(region_code, np.int32)
    out = np.full(cc.shape + (3,), 238, np.uint8)
    # BGR palette; UNKNOWN gets deterministic component tints below.
    palette = {
        "TARGET_SUPPORT": (80, 185, 80),
        "OTHER_SURFACE": (170, 145, 105),
        "AMBIGUOUS_BOUNDARY": (180, 80, 180),
        "TARGET_EVIDENCE_UNMAPPED": (45, 155, 230),
    }
    for code, name in REGION_KIND_BY_CODE.items():
        if name == "UNKNOWN":
            continue
        out[cc == int(code)] = palette.get(name, (180, 180, 180))
    unknown_code = next(k for k, v in REGION_KIND_BY_CODE.items() if v == "UNKNOWN")
    for rid in np.unique(rc[cc == unknown_code]):
        rid = int(rid)
        if rid <= 0:
            continue
        out[rc == rid] = (
            190 + (37 * rid) % 45,
            190 + (61 * rid) % 45,
            190 + (17 * rid) % 45,
        )
    # Region edges.
    edge = np.zeros(rc.shape, bool)
    edge[:, 1:] |= rc[:, 1:] != rc[:, :-1]
    edge[1:, :] |= rc[1:, :] != rc[:-1, :]
    out[edge] = (35, 35, 35)
    return out


def _truth_rgb(missed: np.ndarray, gain: np.ndarray, context_region_code: np.ndarray | None = None) -> np.ndarray:
    # Next-prefix gains are, by definition, a subset of current misses, so a "both" colour
    # would hide every gain. Red = currently missed and not newly covered at the next prefix;
    # cyan = currently missed and newly covered at the next historical prefix. Faint gray
    # lines are the global-arm region edges, for context only.
    out = np.full(missed.shape + (3,), 245, np.uint8)
    if context_region_code is not None:
        rc = np.asarray(context_region_code, np.int32)
        edge = np.zeros(rc.shape, bool)
        edge[:, 1:] |= rc[:, 1:] != rc[:, :-1]
        edge[1:, :] |= rc[1:, :] != rc[:-1, :]
        out[edge] = (200, 200, 200)
    out[np.asarray(missed) > 0] = (35, 35, 230)      # red in RGB display
    out[np.asarray(gain) > 0] = (220, 190, 40)       # cyan in RGB display
    return out


def _panel(img: np.ndarray, title: str, footer: str = "") -> np.ndarray:
    img = np.flipud(img)
    img = cv2.resize(img, (PANEL_W, PANEL_H - 58), interpolation=cv2.INTER_NEAREST)
    out = np.full((PANEL_H, PANEL_W, 3), 250, np.uint8)
    out[36:36 + img.shape[0]] = img
    cv2.putText(out, title, (12, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.57, (20, 20, 20), 1, cv2.LINE_AA)
    if footer:
        scale = 0.38
        while scale > 0.28 and cv2.getTextSize(footer, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)[0][0] > PANEL_W - 20:
            scale -= 0.01
        cv2.putText(out, footer, (10, PANEL_H - 8), cv2.FONT_HERSHEY_SIMPLEX, scale, (40, 40, 40), 1, cv2.LINE_AA)
    return out


def _text_panel(lines: list[str], title: str) -> np.ndarray:
    out = np.full((PANEL_H, PANEL_W, 3), 252, np.uint8)
    cv2.putText(out, title, (12, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.57, (20, 20, 20), 1, cv2.LINE_AA)
    y = 55
    for line in lines:
        if y > PANEL_H - 14:
            break
        cv2.putText(out, line[:90], (14, y), cv2.FONT_HERSHEY_SIMPLEX, 0.43, (30, 30, 30), 1, cv2.LINE_AA)
        y += 20
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("proposal_dir")
    ap.add_argument("evaluation_dir")
    ap.add_argument("out_dir", nargs="?")
    a = ap.parse_args()
    prop = Path(a.proposal_dir)
    evdir = Path(a.evaluation_dir)
    out = Path(a.out_dir or (evdir / "demo"))
    out.mkdir(parents=True, exist_ok=True)
    rows = json.loads((evdir / "state-evaluation.json").read_text(encoding="utf-8"))

    frames: list[Path] = []
    scored: list[tuple[tuple[int, int, int], Path]] = []
    for row in rows:
        gi = int(row["global_index"])
        iid = int(row["instance_id"])
        step = int(row["local_step"])
        imgs = {}
        codes = {}
        for arm in ("local", "global"):
            with np.load(prop / "states" / f"global_{gi:03d}" / arm / "partition.npz", allow_pickle=False) as z:
                imgs[arm] = _region_rgb(np.array(z["class_code"]), np.array(z["region_code"]))
                codes[arm] = np.array(z["region_code"])
        with np.load(evdir / "states" / f"global_{gi:03d}" / "truth-evaluation.npz", allow_pickle=False) as z:
            missed = np.array(z["missed_count"])
            gain = np.array(z["next_gain_count"])

        p1 = _panel(imgs["local"], f"local target-memory partition: g={gi} obj={iid} fix={step}",
                    "green=target | gray-blue=other | tinted=UNKNOWN | purple=ambiguous | orange=target evidence")
        p2 = _panel(imgs["global"], "cross-target causal 3-D memory partition",
                    "same region semantics; only completed-prefix head 3-D memory is global")
        p3 = _panel(_truth_rgb(missed, gain, codes["global"]), "EVALUATION ONLY: current misses / next-prefix gain",
                    "red=missed now | cyan=missed now, covered at next historical prefix | gray=global region edges")
        l, g = row["local"], row["global"]
        cmp = row["global_vs_local_miss_containing_region"]
        lines = [
            f"current reachable / covered / missed: {row['reachable_samples']} / {row['covered_samples']} / {row['missed_samples']}",
            f"next historical prefix newly covers: {row['newly_covered_at_next_prefix']}",
            "",
            f"LOCAL positive candidates: {l['truth_positive_candidate_regions']}",
            f"GLOBAL positive candidates: {g['truth_positive_candidate_regions']}",
            f"LOCAL candidate recall: {l['candidate_recall']}",
            f"GLOBAL candidate recall: {g['candidate_recall']}",
            f"LOCAL miss in >50%-chart positive regions: {l['captured_misses_by_positive_region_area']['gt_50']}",
            f"GLOBAL miss in >50%-chart positive regions: {g['captured_misses_by_positive_region_area']['gt_50']}",
            f"miss containing region smaller/equal/larger: {cmp['smaller']}/{cmp['equal']}/{cmp['larger']}",
            f"median region-area delta (global-local): {cmp['median_chart_fraction_delta']}",
            "",
            "No score/rank/policy is shown. Truth panels and labels are evaluator-only.",
        ]
        p4 = _text_panel(lines, "prefix benchmark diagnostics")
        frame = np.vstack((np.hstack((p1, p2)), np.hstack((p3, p4))))
        fn = out / f"frame_{len(frames):04d}.png"
        cv2.imwrite(str(fn), frame)
        frames.append(fn)
        score = (
            int(cmp["smaller"]),
            int(l["captured_misses_by_positive_region_area"]["gt_50"] - g["captured_misses_by_positive_region_area"]["gt_50"]),
            int(g["truth_positive_candidate_regions"]),
        )
        scored.append((score, iid, fn))

    if frames:
        first = cv2.imread(str(frames[0])); hh, ww = first.shape[:2]
        vw = cv2.VideoWriter(str(out / "partition-graph-7-demo.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), 4.0, (ww, hh))
        if vw.isOpened():
            for f in frames:
                vw.write(cv2.imread(str(f)))
            vw.release()
        # Display selection only: best frame per target by the same descriptive tuple, so the
        # overview shows eight different targets instead of consecutive states of two.
        best: dict[int, tuple[tuple[int, int, int], Path]] = {}
        for s, tid, fn in scored:
            if tid not in best or s > best[tid][0]:
                best[tid] = (s, fn)
        picks = [p for _s, p in sorted(best.values(), key=lambda t: (t[0], str(t[1])), reverse=True)[:8]]
        thumbs = [cv2.resize(cv2.imread(str(p)), (ww // 2, hh // 2), interpolation=cv2.INTER_AREA) for p in picks]
        if thumbs:
            while len(thumbs) % 2:
                thumbs.append(np.full_like(thumbs[0], 255))
            ov = np.vstack([np.hstack(thumbs[i:i+2]) for i in range(0, len(thumbs), 2)])
            cv2.imwrite(str(out / "overview.png"), ov)

    (out / "Demo.md").write_text(
        "# Partition-Graph Phase 7 demo\n\n"
        "Evaluation-side visualization of the 104 historical prefixes. It compares the same current target state under per-target head memory and causal cross-target head memory. No panel is a policy or ranking.\n\n"
        "Panels: local partition; global-memory partition; **EVALUATION ONLY** dense current misses and samples newly covered by the next historical prefix; descriptive metrics. Positive pitch is up.\n\n"
        "Region key: green target support; gray-blue measured other surface; individually tinted UNKNOWN components; purple ambiguous boundary; orange target evidence measured but not in the current target map.\n\n"
        "Truth key (EVALUATION ONLY): red = reachable target sample missed by the current prefix map and not newly covered at the next historical prefix; "
        "cyan = missed now and newly covered at the next historical prefix (next-prefix gains are always a subset of current misses). "
        "Faint gray lines are the global-arm region edges, for context. The overview shows the best frame per target by a descriptive tuple "
        "(misses moved to a smaller region, reduction of misses in >50%-chart regions, global positive candidates); it is a display selection, not a ranking.\n\n"
        f"Frames: {len(frames)}.\n",
        encoding="utf-8",
    )
    print(f"[partition-graph7-demo] wrote {len(frames)} frames to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
