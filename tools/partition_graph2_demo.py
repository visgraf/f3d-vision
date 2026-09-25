#!/usr/bin/env python3
"""Generate a four-panel demo from a Partition-Graph-2 lift."""
from __future__ import annotations
import argparse, json, math
from pathlib import Path
import sys
import cv2
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from fov3d.scene import ScenePartitionGraph, RegionKind

PANEL_W, PANEL_H = 620, 360

def _palette(labels: np.ndarray, base=(30,30,30)) -> np.ndarray:
    out = np.zeros(labels.shape + (3,), np.uint8)
    out[:] = base
    for lab in np.unique(labels):
        if lab <= 0: continue
        x = int(lab)
        out[labels == lab] = ((53*x+70)%205+30, (97*x+20)%205+30, (151*x+10)%205+30)
    return out

def _panel(img: np.ndarray, title: str) -> np.ndarray:
    img = cv2.resize(img, (PANEL_W, PANEL_H-36), interpolation=cv2.INTER_NEAREST)
    out = np.full((PANEL_H, PANEL_W, 3), 245, np.uint8)
    out[36:] = img
    cv2.putText(out, title, (12,25), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (20,20,20), 1, cv2.LINE_AA)
    return out

def _text_panel(lines: list[str], title: str) -> np.ndarray:
    out = np.full((PANEL_H, PANEL_W, 3), 250, np.uint8)
    cv2.putText(out, title, (12,25), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (20,20,20), 1, cv2.LINE_AA)
    y=58
    for line in lines[:15]:
        cv2.putText(out, line[:82], (14,y), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (30,30,30), 1, cv2.LINE_AA); y+=20
    return out

def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("lift_dir"); ap.add_argument("out_dir", nargs="?")
    a=ap.parse_args(); lift=Path(a.lift_dir); out=Path(a.out_dir or (lift/"demo")); out.mkdir(parents=True,exist_ok=True)
    summary=json.loads((lift/"summary.json").read_text())
    frames=[]; rows=[]
    for obj in summary["objects"]:
        iid=int(obj["instance_id"])
        for fs in obj["fixations"]:
            if not fs.get("map_present"): continue
            step=int(fs["step"]); d=lift/"objects"/f"instance_{iid:04d}"/f"fix_{step:02d}"
            with np.load(d/"state.npz",allow_pickle=False) as z:
                ol=np.array(z["object_labels"]); bl=np.array(z["base_labels"]); vis=np.array(z["visibility"])
            p1=_panel(_palette(ol), f"target partition: instance {iid}, fix {step}")
            p2=_panel(_palette(bl, base=(245,245,245)), "BASE connected components")
            vis_rgb=np.zeros(vis.shape+(3,),np.uint8)
            vis_rgb[vis==0]=(35,35,35); vis_rgb[vis==1]=(220,120,60); vis_rgb[vis==2]=(60,150,220); vis_rgb[vis==3]=(90,200,100)
            p3=_panel(vis_rgb,"observation overlay: dark=unseen, L/R/binocular")
            rel=json.loads((d/"relations.json").read_text())
            lines=[
                f"object components: {fs['object_components']}", f"BASE components: {fs['base_components']}",
                f"dual edges: {fs['dual_edges']}", f"same-object pairs: {fs['same_object_component_pairs']}",
                f"pairs sharing BASE: {fs['pairs_with_shared_base_neighbor']}", f"topology event: {fs['topology_event']}",
                "", "Shared-BASE relations:",
            ]
            for r in rel[:7]: lines.append(f"{r['region_a']} <-> {r['region_b']}: {','.join(r['shared_base_regions']) or '-'}")
            p4=_text_panel(lines,"dual/topological query (no policy)")
            frame=np.vstack((np.hstack((p1,p2)),np.hstack((p3,p4))))
            fn=out/f"frame_{len(frames):04d}.png"; cv2.imwrite(str(fn),frame); frames.append(fn)
            rows.append((iid,step,fs))
    if frames:
        first=cv2.imread(str(frames[0])); h,w=first.shape[:2]
        vw=cv2.VideoWriter(str(out/"partition-graph-2-demo.mp4"),cv2.VideoWriter_fourcc(*"mp4v"),4.0,(w,h))
        if vw.isOpened():
            for f in frames: vw.write(cv2.imread(str(f)))
            vw.release()
        # Overview: choose up to 6 final object frames with most components/base complexity.
        finals=[]
        for obj in summary["objects"]:
            valid=[x for x in obj["fixations"] if x.get("map_present")]
            if valid:
                f=valid[-1]; score=(f["object_components"]>1, f["object_components"], f["base_components"])
                finals.append((score,int(obj["instance_id"]),int(f["step"])))
        finals=sorted(finals,reverse=True)[:6]
        thumbs=[]
        for _,iid,step in finals:
            idx=next(i for i,(ii,ss,_) in enumerate(rows) if ii==iid and ss==step)
            im=cv2.imread(str(frames[idx])); thumbs.append(cv2.resize(im,(640,400)))
        if thumbs:
            while len(thumbs)%2: thumbs.append(np.full_like(thumbs[0],255))
            ov=np.vstack([np.hstack(thumbs[i:i+2]) for i in range(0,len(thumbs),2)])
            cv2.imwrite(str(out/"overview.png"),ov)
    (out/"Demo.md").write_text(
        "# Partition-Graph Phase 2 demo\n\n"
        "Post-hoc visualization of saved controller-time state. No panel participated in gaze selection. "
        "No dense Blender evaluation truth is used.\n\n"
        "Panels show the target partition, BASE components, accumulated binocular observation overlay, "
        "and graph-derived same-object/shared-BASE relations.\n\n"
        f"Frames: {len(frames)}\n\nRegenerate with:\n\n```bash\n./.venv/bin/python tools/partition_graph2_demo.py {lift} {out}\n```\n",
        encoding="utf-8")
    print(f"[partition-graph2-demo] wrote {len(frames)} frames to {out}")
    return 0
if __name__=="__main__": raise SystemExit(main())
