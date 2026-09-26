#!/usr/bin/env python3
"""Generate the Phase-8 historical-global vs integrated residual demo."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import sys
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PANEL_W, PANEL_H = 626, 560


def _id_color(i: int) -> tuple[int,int,int]:
    x=int(i); return ((53*x+70)%190+35,(97*x+20)%190+35,(151*x+10)%190+35)


def _region_rgb(rc: np.ndarray, regions: list[dict]) -> np.ndarray:
    # BGR. Semantic kinds use saturated reserved colours; every UNKNOWN component gets a pale
    # pastel tint (never saturated, so it cannot be mistaken for a semantic kind) and region
    # edges are drawn dark so separate UNKNOWN components stay distinguishable.
    out=np.full(rc.shape+(3,),238,np.uint8)
    by={int(r["region_code"]):r for r in regions}
    for code in np.unique(rc):
        c=int(code); r=by.get(c)
        if not r: continue
        kind=str(r["kind"])
        if kind=="TARGET_SUPPORT": color=(70,190,70)            # green
        elif kind=="OTHER_SURFACE": color=(150,125,105)       # gray-blue
        elif kind=="TARGET_EVIDENCE_UNMAPPED": color=(180,80,220)  # magenta
        elif kind=="AMBIGUOUS_BOUNDARY": color=(70,180,220)   # orange
        else: color=(200+(37*c)%40,200+(61*c)%40,200+(17*c)%40)  # pale UNKNOWN tint
        out[rc==c]=color
    edge=np.zeros(rc.shape,bool)
    edge[:,1:]|=rc[:,1:]!=rc[:,:-1]; edge[1:,:]|=rc[1:,:]!=rc[:-1,:]
    out[edge]=(60,60,60)
    return out


def _panel(img: np.ndarray, title: str, footer: str="") -> np.ndarray:
    x=cv2.resize(np.flipud(img),(PANEL_W,PANEL_H-58),interpolation=cv2.INTER_NEAREST)
    out=np.full((PANEL_H,PANEL_W,3),247,np.uint8); out[36:36+x.shape[0]]=x
    cv2.putText(out,title,(12,25),cv2.FONT_HERSHEY_SIMPLEX,.58,(20,20,20),1,cv2.LINE_AA)
    if footer:
        s=.38
        while s>.28 and cv2.getTextSize(footer,cv2.FONT_HERSHEY_SIMPLEX,s,1)[0][0]>PANEL_W-20: s-=.01
        cv2.putText(out,footer,(10,PANEL_H-8),cv2.FONT_HERSHEY_SIMPLEX,s,(40,40,40),1,cv2.LINE_AA)
    return out


def _truth_rgb(hist: np.ndarray, gain: np.ndarray, residual: np.ndarray) -> np.ndarray:
    out=np.full(hist.shape+(3,),245,np.uint8)
    out[hist>0]=(170,170,170)
    out[gain>0]=(230,190,40)      # cyan-ish in BGR
    out[residual>0]=(35,35,235)   # red
    return out


def _text(lines: list[str], title: str) -> np.ndarray:
    out=np.full((PANEL_H,PANEL_W,3),250,np.uint8)
    cv2.putText(out,title,(12,25),cv2.FONT_HERSHEY_SIMPLEX,.58,(20,20,20),1,cv2.LINE_AA)
    y=56
    for line in lines:
        if y>PANEL_H-18: break
        cv2.putText(out,line[:90],(14,y),cv2.FONT_HERSHEY_SIMPLEX,.44,(30,30,30),1,cv2.LINE_AA); y+=20
    return out


def main()->int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("proposal_dir"); ap.add_argument("evaluation_dir"); ap.add_argument("out_dir",nargs="?")
    a=ap.parse_args(); prop=Path(a.proposal_dir); ev=Path(a.evaluation_dir); out=Path(a.out_dir or (ev/"demo")); out.mkdir(parents=True,exist_ok=True)
    ps=json.loads((prop/"summary.json").read_text()); es=json.loads((ev/"summary.json").read_text()); states=json.loads((ev/"state-evaluation.json").read_text())
    p7=Path(ps["phase7_proposal_dir"])
    frames=[]; picks=[]
    for s in states:
        gi=int(s["global_index"]); iid=int(s["instance_id"]); step=int(s["local_step"])
        with np.load(p7/"states"/f"global_{gi:03d}"/"global"/"partition.npz",allow_pickle=False) as z: hrc=np.array(z["region_code"])
        hr=json.loads((p7/"states"/f"global_{gi:03d}"/"global"/"regions.json").read_text())
        with np.load(prop/"states"/f"global_{gi:03d}"/"integrated"/"partition.npz",allow_pickle=False) as z: irc=np.array(z["region_code"])
        ir=json.loads((prop/"states"/f"global_{gi:03d}"/"integrated"/"regions.json").read_text())
        with np.load(ev/"states"/f"global_{gi:03d}"/"truth-evaluation.npz",allow_pickle=False) as z:
            hm=np.array(z["historical_miss_count"]); ig=np.array(z["integration_gain_count"]); rm=np.array(z["residual_miss_count"])
        p1=_panel(_region_rgb(hrc,hr),f"Phase-7 historical global: g{gi} target {iid} fix {step}",
                  "green=target | magenta=measured target, unmapped | gray-blue=other | orange=ambiguous | pale=UNKNOWN")
        p2=_panel(_region_rgb(irc,ir),"Phase-8 integrated target support",
                  "same key; magenta is empty after integration; UNKNOWN/OTHER_SURFACE are unranked candidates")
        p3=_panel(_truth_rgb(hm,ig,rm),"EVALUATION ONLY: historical miss -> integration gain / residual",
                  "cyan=covered by integration, no new look | red=residual miss (historical misses = cyan + red)")
        m=s["integrated"]; lines=[
            f"historical missed: {s['historical_missed_samples']}",
            f"integration gain: {s['integration_gain_samples']}",
            f"residual misses: {s['integrated_residual_misses']}",
            f"positive candidate regions: {m['truth_positive_candidate_regions']}",
            f"residual candidate recall: {m['candidate_recall_on_residual']}",
            f"target-evidence-unmapped residual: {m['target_evidence_unmapped_residual_misses']}",
            f"target-support residual: {m['target_support_residual_misses']}",
            "",
            "No score / no ranking / no gaze policy",
        ]
        p4=_text(lines,"integration / residual benchmark summary")
        frame=np.vstack((np.hstack((p1,p2)),np.hstack((p3,p4))))
        fn=out/f"frame_{len(frames):04d}.png"; cv2.imwrite(str(fn),frame); frames.append(fn)
        picks.append((int(s['integration_gain_samples']),int(s['integrated_residual_misses']),iid,fn))
    if frames:
        first=cv2.imread(str(frames[0])); h,w=first.shape[:2]
        vw=cv2.VideoWriter(str(out/"partition-graph-8-demo.mp4"),cv2.VideoWriter_fourcc(*"mp4v"),4.0,(w,h))
        if vw.isOpened():
            for f in frames: vw.write(cv2.imread(str(f)))
            vw.release()
        # Display selection only: the frame with the most historical misses (gain + residual) for
        # each target, then the eight targets with the most, so the overview shows both measured
        # integration gain and residual structure across different targets.
        best={}
        for g,r,tid,fn in picks:
            key=(g+r,g,r,str(fn))
            if tid not in best or key>best[tid][0]: best[tid]=(key,fn)
        chosen=[fn for _k,fn in sorted(best.values(),reverse=True)[:8]]
        thumbs=[cv2.resize(cv2.imread(str(p)),(w//2,h//2),interpolation=cv2.INTER_AREA) for p in chosen]
        if thumbs:
            if len(thumbs)%2: thumbs.append(np.full_like(thumbs[0],255))
            ov=np.vstack([np.hstack(thumbs[i:i+2]) for i in range(0,len(thumbs),2)])
            cv2.imwrite(str(out/"overview.png"),ov)
    (out/"Demo.md").write_text(
        "# Partition-Graph Phase 8 demo\n\n"
        "Historical-global and shadow-integrated target representations are shown side by side. "
        "The lower-left panel is **EVALUATION ONLY**: gray marks historical misses, cyan marks misses "
        "covered without a new look by causal target-evidence integration, and red marks the residual. "
        "No panel shows an attention score, ranking or policy. Positive pitch is up.\n\n"
        "Region key (both upper panels): green TARGET_SUPPORT; magenta TARGET_EVIDENCE_UNMAPPED (measured target geometry "
        "not in the target map; empty after integration); gray-blue OTHER_SURFACE; orange AMBIGUOUS_BOUNDARY; pale tints = "
        "individual UNKNOWN components (tints are arbitrary and differ between panels because region codes are renumbered; "
        "dark lines are region edges).\n\n"
        "Truth key (EVALUATION ONLY): cyan = historically missed sample covered by integrating already-measured target "
        "geometry, with no new look; red = residual miss. Every historical miss is exactly one of the two, so no separate "
        "gray layer is visible. The overview shows, for each of the eight targets with the most historical misses, its frame "
        "with the most historical misses; this is a display selection, not a ranking.\n\n"
        f"Frames: {len(frames)}.\n", encoding="utf-8")
    print(f"[partition-graph8-demo] wrote {len(frames)} frames to {out}")
    return 0

if __name__=="__main__": raise SystemExit(main())
