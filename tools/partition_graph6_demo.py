#!/usr/bin/env python3
"""Generate an evaluation-only Phase-6 overview of causal regions and missed truth."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import sys
import cv2
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from fov3d.experiments.classroom_partition.benchmark import REGION_KIND, _grid, _cells, _covered

PANEL_W, PANEL_H = 640, 520

def _class_rgb(a: np.ndarray) -> np.ndarray:
    out = np.zeros(a.shape + (3,), np.uint8)
    # BGR palette.  Semantics are written explicitly in Demo.md.
    out[a == REGION_KIND["TARGET_SUPPORT"]] = (40, 210, 245)
    out[a == REGION_KIND["OTHER_SURFACE"]] = (170, 170, 170)
    out[a == REGION_KIND["UNKNOWN"]] = (45, 45, 45)
    out[a == REGION_KIND["AMBIGUOUS_BOUNDARY"]] = (180, 80, 180)
    out[a == REGION_KIND["TARGET_EVIDENCE_UNMAPPED"]] = (80, 180, 80)
    return out

def _region_rgb(rc: np.ndarray, regions: list[dict]) -> np.ndarray:
    # BGR. Distinct regions must stay distinguishable: every UNKNOWN region gets its own dark
    # tint, OTHER_SURFACE regions get muted gray-blue tones (never green, which panel 1 reserves
    # for TARGET_EVIDENCE_UNMAPPED), and region boundaries are drawn in white.
    out = np.full(rc.shape + (3,), 235, np.uint8)
    unk = other = 0
    for r in sorted(regions, key=lambda r: -int(r["cell_count"])):
        code = int(r["region_code"])
        if r["kind"] == "TARGET_SUPPORT": col = (40,210,245)
        elif r["kind"] == "UNKNOWN":
            k = unk; unk += 1
            col = (35 + (37*k) % 50, 30 + (23*k) % 40, 40 + (53*k) % 60) if k else (45, 45, 45)
        elif r["kind"] == "OTHER_SURFACE":
            k = other; other += 1; g = 120 + (29*k) % 80
            col = (g + 30 if g + 30 < 256 else 255, g, g - 20)
        elif r["kind"] == "AMBIGUOUS_BOUNDARY": col = (180,80,180)
        else: col = (80,180,80)
        out[rc == code] = col
    edge = np.zeros(rc.shape, bool)
    edge[:, 1:] |= rc[:, 1:] != rc[:, :-1]; edge[1:, :] |= rc[1:, :] != rc[:-1, :]
    out[edge] = (250, 250, 250)
    return out

def _panel(img: np.ndarray, title: str, footer: str = "") -> np.ndarray:
    img = np.flipud(img)
    img = cv2.resize(img, (PANEL_W, PANEL_H-58), interpolation=cv2.INTER_NEAREST)
    out = np.full((PANEL_H, PANEL_W, 3), 248, np.uint8)
    out[36:36+img.shape[0]] = img
    cv2.putText(out, title, (12,25), cv2.FONT_HERSHEY_SIMPLEX, .58, (20,20,20), 1, cv2.LINE_AA)
    if footer:
        cv2.putText(out, footer[:96], (12,PANEL_H-8), cv2.FONT_HERSHEY_SIMPLEX, .39, (30,30,30), 1, cv2.LINE_AA)
    return out

def _text(lines: list[str], title: str) -> np.ndarray:
    out = np.full((PANEL_H, PANEL_W, 3), 250, np.uint8)
    cv2.putText(out,title,(12,25),cv2.FONT_HERSHEY_SIMPLEX,.58,(20,20,20),1,cv2.LINE_AA)
    y=55
    for line in lines:
        if y>PANEL_H-15: break
        cv2.putText(out,line[:92],(14,y),cv2.FONT_HERSHEY_SIMPLEX,.44,(30,30,30),1,cv2.LINE_AA); y+=20
    return out

def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source_run")
    ap.add_argument("proposal_dir")
    ap.add_argument("evaluation_dir")
    ap.add_argument("out_dir", nargs="?")
    a=ap.parse_args()
    source=Path(a.source_run); prop=Path(a.proposal_dir); ev=Path(a.evaluation_dir); out=Path(a.out_dir or (ev/"demo")); out.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((source/"manifest.json").read_text())
    seeds=json.loads((source/"bootstrap"/"seeds.json").read_text())
    domain=seeds["controller_domain_deg"]; y0,_y1,p0,_p1,h,w=_grid(domain,.1)
    with np.load(source/"bootstrap"/"evaluation_only"/"reachable_samples.npz",allow_pickle=False) as z:
        tids=np.asarray(z["instance_id"],np.int32); tang=np.asarray(z["yaw_pitch_deg"],np.float64); txyz=np.asarray(z["xyz_h"],np.float64)
    eval_summary=json.loads((ev/"summary.json").read_text())
    eval_by={int(r["instance_id"]):r for r in eval_summary["targets"]}
    frames=[]
    for obj in manifest["objects"]:
        iid=int(obj["instance_id"]); td=prop/"targets"/f"instance_{iid:04d}"
        with np.load(td/"partition.npz",allow_pickle=False) as z:
            cls=np.asarray(z["class_code"],np.uint8); rc=np.asarray(z["region_code"],np.int32)
        regions=json.loads((td/"regions.json").read_text())
        # Missed sample positions are taken from evaluator's region totals only indirectly;
        # recompute coverage is intentionally avoided here.  Instead plot all reachable target
        # truth cells and distinguish the evaluator's aggregate in the text panel.  The demo is
        # illustrative and evaluation-only, never a policy input.
        # Evaluation-only: recompute the sealed 12 mm coverage with the evaluator's own function so
        # missed and covered target samples can be told apart. Nothing is written anywhere.
        mask=tids==iid
        with np.load(source/"objects"/f"instance_{iid:04d}"/"final_map.npz",allow_pickle=False) as z:
            sm=np.asarray(z["xyz_h"],np.float64)
        sm=sm[np.isfinite(sm).all(axis=1)]
        cov=_covered(txyz[mask],sm,0.012)
        r=eval_by[iid]
        if int((~cov).sum())!=int(r["missed_samples"]):
            raise RuntimeError(f"demo coverage recount disagrees with evaluator for {iid}")
        truth_img=_region_rgb(rc,regions)
        for sel,col in ((cov,(230,200,0)),(~cov,(0,0,255))):  # covered cyan, then missed red on top
            yy,xx,ok=_cells(tang[mask][sel,0],tang[mask][sel,1],y0,p0,.1,h,w)
            for y,x in zip(yy[ok],xx[ok]):
                cv2.circle(truth_img,(int(x),int(y)),1,col,-1)
        p1=_panel(_class_rgb(cls),f"causal evidence classes: {iid} {obj['object_name']}","yellow=target | gray=other depth | dark=unknown | purple=ambiguous | green=target evidence")
        p2=_panel(_region_rgb(rc,regions),"epistemic regions (causal, truth-free, unranked)","yellow=target | dark tints=UNKNOWN regions | gray-blue=OTHER_SURFACE | white=region edges")
        p3=_panel(truth_img,"EVALUATION ONLY: dense reachable target truth","red=missed target sample | cyan=covered | truth never enters the proposal tree")
        lines=[
            f"reachable: {r['reachable_samples']}", f"covered: {r['covered_samples']}", f"missed: {r['missed_samples']}",
            f"candidate-captured misses: {r['candidate_captured_missed_samples']}",
            f"candidate recall: {r['candidate_recall'] if r['candidate_recall'] is not None else '-'}",
            f"truth-positive candidate regions: {r['truth_positive_candidate_regions']}",
            f"miss components (0.25 deg): {r['miss_component_count_025deg']}", "",
        ] + [f"misses in {k}: {v}" for k,v in sorted(r["missed_by_region_kind"].items())]
        p4=_text(lines,"offline truth evaluation (descriptive only)")
        frame=np.vstack((np.hstack((p1,p2)),np.hstack((p3,p4))))
        fn=out/f"frame_{len(frames):04d}.png"; cv2.imwrite(str(fn),frame); frames.append(fn)
    if frames:
        first=cv2.imread(str(frames[0])); hh,ww=first.shape[:2]
        vw=cv2.VideoWriter(str(out/"partition-graph-6-demo.mp4"),cv2.VideoWriter_fourcc(*"mp4v"),2.0,(ww,hh))
        if vw.isOpened():
            for f in frames: vw.write(cv2.imread(str(f)))
            vw.release()
        thumbs=[cv2.resize(cv2.imread(str(f)),(ww//4,hh//4),interpolation=cv2.INTER_AREA) for f in frames]
        rows=[]
        for i in range(0,len(thumbs),5):
            row=thumbs[i:i+5]
            while len(row)<5: row.append(np.full_like(thumbs[0],255))
            rows.append(np.hstack(row))
        cv2.imwrite(str(out/"overview.png"),np.vstack(rows))
    (out/"Demo.md").write_text(
        "# Partition-Graph Phase 6 demo\n\nEvaluation-only visualization. Dense truth is used only in the evaluation panels and never appears in the causal proposal tree.\n\n"
        "Evidence key: yellow TARGET_SUPPORT; gray OTHER_SURFACE; dark UNKNOWN; purple AMBIGUOUS_BOUNDARY; green TARGET_EVIDENCE_UNMAPPED. "
        "Only UNKNOWN and OTHER_SURFACE are emitted as attention *candidates*, and Phase 6 assigns no score or gaze.\n\n"
        "Region panel (causal, truth-free): yellow TARGET_SUPPORT; each UNKNOWN region has its own dark tint (the largest is plain dark gray); "
        "OTHER_SURFACE regions are gray-blue tones; purple AMBIGUOUS_BOUNDARY; white lines are region boundaries.\n\n"
        "Truth panel (EVALUATION ONLY): the same region raster with dense reachable target samples of this target: red = missed by the sealed "
        "12 mm coverage test, cyan = covered. Coverage is recomputed with the evaluator's own function and checked against the evaluator's "
        "per-target missed count. Truth never enters the proposal tree and is not a controller feature.\n\n"
        f"Frames: {len(frames)}. Regenerate with `./.venv/bin/python tools/partition_graph6_demo.py {source} {prop} {ev} {out}`.\n",
        encoding="utf-8")
    print(f"[partition-graph6-demo] wrote {len(frames)} frames to {out}")
    return 0

if __name__=="__main__": raise SystemExit(main())
