#!/usr/bin/env python3
"""Generate a compact demo for Phase-5 unresolved historical-prefix relations."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import cv2
import numpy as np

PANEL_W, PANEL_H = 626, 560
PALETTE = {
    "TARGET_SUPPORT": (40,210,245),
    "MAPPED_OTHER": (150,150,150),
    "INCIDENTAL_OTHER_DEPTH": (70,190,70),
    "AMBIGUOUS_DEPTH_INSTANCE": (190,80,190),
    "SEEN_NO_HEAD_DEPTH": (220,180,80),
    "UNSEEN": (35,35,35),
}

def _id_color(iid:int)->tuple[int,int,int]:
    return ((53*iid+70)%190+35,(97*iid+20)%190+35,(151*iid+10)%190+35)

def _panel(img:np.ndarray,title:str,footer:str="")->np.ndarray:
    img=np.flipud(img)
    img=cv2.resize(img,(PANEL_W,PANEL_H-58),interpolation=cv2.INTER_NEAREST)
    out=np.full((PANEL_H,PANEL_W,3),247,np.uint8); out[36:36+img.shape[0]]=img
    cv2.putText(out,title,(12,25),cv2.FONT_HERSHEY_SIMPLEX,0.58,(20,20,20),1,cv2.LINE_AA)
    if footer:
        s=0.38
        while s>0.28 and cv2.getTextSize(footer,cv2.FONT_HERSHEY_SIMPLEX,s,1)[0][0]>PANEL_W-20: s-=0.01
        cv2.putText(out,footer,(10,PANEL_H-8),cv2.FONT_HERSHEY_SIMPLEX,s,(40,40,40),1,cv2.LINE_AA)
    return out

def _text(lines:list[str],title:str)->np.ndarray:
    out=np.full((PANEL_H,PANEL_W,3),250,np.uint8); cv2.putText(out,title,(12,25),cv2.FONT_HERSHEY_SIMPLEX,0.58,(20,20,20),1,cv2.LINE_AA)
    y=55
    for line in lines:
        if y>PANEL_H-18: break
        cv2.putText(out,line[:90],(14,y),cv2.FONT_HERSHEY_SIMPLEX,0.43,(30,30,30),1,cv2.LINE_AA); y+=20
    return out

def main()->int:
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument("phase5_dir"); ap.add_argument("out_dir",nargs="?"); a=ap.parse_args()
    root=Path(a.phase5_dir); out=Path(a.out_dir or root/"demo"); out.mkdir(parents=True,exist_ok=True)
    challenges=json.loads((root/"challenge-states.json").read_text())
    frames=[]
    for row in challenges:
        gi=int(row["global_index"]); iid=int(row["instance_id"]); sd=root/"states"/f"global_{gi:03d}"
        rels=json.loads((sd/"relations.json").read_text())
        with np.load(sd/"head-evidence.npz",allow_pickle=False) as z:
            support=np.array(z["target_support"],bool); owner=np.array(z["owner_instance"],np.int32); seen=np.array(z["seen_any"],bool)
            nearest=np.array(z["nearest_instance"],np.int32); amb=np.array(z["ambiguous_instance"],bool)
        base=np.full(support.shape+(3,),235,np.uint8); base[support]=PALETTE["TARGET_SUPPORT"]
        for oid in np.unique(owner):
            if int(oid)>0 and int(oid)!=iid: base[owner==oid]=_id_color(int(oid))
        # Same exclusive precedence as incidental.annotate_head_relation, with the target's own
        # support first (HEAD_CLASS_NAMES order), so target cells are not shown as "no depth".
        other=(nearest>0)&(nearest!=iid)
        ev=np.full_like(base,PALETTE["UNSEEN"]); ev[seen]=PALETTE["SEEN_NO_HEAD_DEPTH"]
        ev[other&~amb]=PALETTE["INCIDENTAL_OTHER_DEPTH"]; ev[other&amb]=PALETTE["AMBIGUOUS_DEPTH_INSTANCE"]
        ev[(owner>0)&(owner!=iid)]=PALETTE["MAPPED_OTHER"]; ev[support]=PALETTE["TARGET_SUPPORT"]
        corr=base.copy(); unresolved=[]; marks=[]
        for r in rels:
            if r.get("relation_origin")!="own_support_gap" or not r.get("has_unresolved_true_gap"): continue
            unresolved.append(r)
            for y,x in r.get("true_gap_yx",[]):
                expl=(owner[y,x]>0 and owner[y,x]!=iid) or (nearest[y,x]>0 and nearest[y,x]!=iid and not amb[y,x])
                if expl: corr[y,x]=(0,140,255)            # explained true-gap cell (mapped/incidental other)
                else: corr[y,x]=(20,20,240); marks.append((y,x))  # unresolved true-gap cell
        p1=_panel(base,f"state {gi}: target {iid} partition/support","yellow=target support | colors/gray=other mapped objects")
        p2=_panel(ev,"head-centred controller-time depth evidence",
                  "yellow=target | gray=mapped other | green=incidental other depth | purple=ambiguous | blue=seen, no head depth | dark=unseen")
        p3=_panel(corr,"unresolved true-gap cells (circled)","red+circle=unresolved true-gap cell | orange=explained true-gap cell")
        sy=(PANEL_H-58)/support.shape[0]; sx=PANEL_W/support.shape[1]
        for y,x in marks:  # display-only emphasis: single cells are otherwise ~1 px
            cy=int(36+(support.shape[0]-1-y+0.5)*sy); cx=int((x+0.5)*sx)
            cv2.circle(p3,(cx,cy),9,(20,20,240),2,cv2.LINE_AA)
        lines=[f"object: {row['object_name']} ({iid})",f"historical prefix fix: {row['local_step']}",f"unresolved relations in selected state: {len(unresolved)}",""]
        for r in unresolved[:12]:
            c=r["head_evidence_class_counts"]; lines.append(f"gap {r.get('region_a')} -> {r.get('region_b')}: U={c['UNSEEN']} S={c['SEEN_NO_HEAD_DEPTH']} A={c['AMBIGUOUS_DEPTH_INSTANCE']}")
        p4=_text(lines,"Phase-5 challenge relation summary (descriptive only)")
        frame=np.vstack((np.hstack((p1,p2)),np.hstack((p3,p4)))); fn=out/f"frame_{len(frames):04d}.png"; cv2.imwrite(str(fn),frame); frames.append(fn)
    if frames:
        first=cv2.imread(str(frames[0])); h,w=first.shape[:2]; vw=cv2.VideoWriter(str(out/"partition-graph-5-demo.mp4"),cv2.VideoWriter_fourcc(*"mp4v"),2.0,(w,h))
        if vw.isOpened():
            for f in frames: vw.write(cv2.imread(str(f)))
            vw.release()
        thumbs=[cv2.resize(cv2.imread(str(f)),(w//3,h//3),interpolation=cv2.INTER_AREA) for f in frames[:9]]
        if thumbs:
            while len(thumbs)%3: thumbs.append(np.full_like(thumbs[0],255))
            cv2.imwrite(str(out/"overview.png"),np.vstack([np.hstack(thumbs[i:i+3]) for i in range(0,len(thumbs),3)]))
    (out/"Demo.md").write_text(
        "# Partition-Graph Phase 5 demo\n\nShows one deterministic earliest unresolved historical-prefix state per target. This is retrospective representation analysis only; no gaze was selected. Evidence is projected from saved binocular-valid `xyz_h` into the head-origin chart.\n\n"
        f"Frames: {len(frames)} (one per compact challenge state). Positive pitch is up.\n\n"
        "## Keys and semantics\n\n"
        "Evidence panel (exclusive classes, precedence top to bottom, as in the relation classifier):\n\n"
        "| colour | class | meaning |\n|---|---|---|\n"
        "| yellow | `TARGET_SUPPORT` | inside the current target's own 12 mm support |\n"
        "| gray | `MAPPED_OTHER` | owned by another reconstructed object in the causal joint partition |\n"
        "| purple | `AMBIGUOUS_DEPTH_INSTANCE` | valid 3-D samples of more than one inherited instance id fell in this 0.1-degree cell |\n"
        "| green | `INCIDENTAL_OTHER_DEPTH` | nearest valid 3-D sample is a non-target instance not owning the cell in the partition |\n"
        "| blue | `SEEN_NO_HEAD_DEPTH` | exact historical `seen_any` sampled the cell, but no valid head-centred 3-D sample landed there |\n"
        "| dark | `UNSEEN` | no historical supported-core sample reached the cell |\n\n"
        "Unresolved-cell panel: red cells, each circled, are unresolved true-gap cells (ambiguous, seen without head depth, unseen) "
        "of own-support-gap relations; orange cells are explained true-gap cells (mapped or incidental other depth) of the same relations. "
        "Circles are display-only emphasis.\n\n"
        "`seen_any` is the exact historical eye-ray raster; head depth is head-origin projected. Instance ids are inherited Oracle-1 labels. "
        "Mapped or incidental other-object depth is not an occlusion verdict.\n",
        encoding="utf-8")
    print(f"[partition-graph5-demo] wrote {len(frames)} challenge frames to {out}")
    return 0
if __name__=="__main__": raise SystemExit(main())
