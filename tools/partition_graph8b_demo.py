#!/usr/bin/env python3
"""Generate a Phase-8b budget-scenario benchmark demo."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import sys
import cv2,numpy as np
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from fov3d.experiments.classroom_partition.benchmark import REGION_KIND

W,H=520,440

def panel(img,title,footer=''):
    x=np.flipud(np.asarray(img,np.uint8)); x=cv2.resize(x,(W,H-58),interpolation=cv2.INTER_NEAREST)
    out=np.full((H,W,3),248,np.uint8); out[34:34+x.shape[0]]=x
    cv2.putText(out,title[:68],(10,23),cv2.FONT_HERSHEY_SIMPLEX,.50,(20,20,20),1,cv2.LINE_AA)
    if footer: cv2.putText(out,footer[:82],(10,H-8),cv2.FONT_HERSHEY_SIMPLEX,.36,(40,40,40),1,cv2.LINE_AA)
    return out

def base_rgb(cc):
    out=np.full(cc.shape+(3,),238,np.uint8)
    out[cc==REGION_KIND['TARGET_SUPPORT']]=(80,190,90); out[cc==REGION_KIND['OTHER_SURFACE']]=(170,130,80)
    out[cc==REGION_KIND['UNKNOWN']]=(225,225,225); out[cc==REGION_KIND['AMBIGUOUS_BOUNDARY']]=(160,80,190)
    out[cc==REGION_KIND['TARGET_EVIDENCE_UNMAPPED']]=(190,70,190); return out

def refined_rgb(rc,regions):
    out=np.full(rc.shape+(3,),238,np.uint8)
    for r in regions:
        m=rc==int(r['region_code']); kind=r['kind']
        if kind=='TARGET_SUPPORT': col=(80,190,90)
        elif kind=='OTHER_SURFACE': col=(165,125,80) if r['eligible_candidate'] else (220,195,170)
        elif kind=='UNKNOWN':
            sh=int(r.get('unknown_shell_index') or 0); v=max(145,240-18*sh); col=(v,v,min(255,v+10)) if r['eligible_candidate'] else (245,225,205)
        else: col=(175,175,175)
        out[m]=col
    edge=np.zeros(rc.shape,bool); edge[:,1:]|=rc[:,1:]!=rc[:,:-1]; edge[1:,:]|=rc[1:,:]!=rc[:-1,:]; out[edge]=(45,45,45)
    return out

def truth_rgb(count):
    out=np.full(count.shape+(3,),245,np.uint8); out[np.asarray(count)>0]=(40,40,235); return out

def main()->int:
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('proposal_dir'); ap.add_argument('evaluation_dir'); ap.add_argument('out_dir'); a=ap.parse_args()
    p=Path(a.proposal_dir); ev=Path(a.evaluation_dir); out=Path(a.out_dir); out.mkdir(parents=True,exist_ok=True)
    rows=json.loads((ev/'state-evaluation.json').read_text())
    # Evaluation-side selection: one highest-residual target frame per scenario.
    picks=[]
    for scenario in ['budget_1','budget_2','budget_4','budget_8','full']:
        q=[r for r in rows if r['scenario']==scenario]
        if q: picks.append(max(q,key=lambda r:(int(r['integrated_residual_misses']),-int(r['instance_id']))))
    frames=[]
    for r in picks:
        s=r['scenario']; iid=int(r['instance_id']); pd=p/'scenarios'/s/'targets'/f'instance_{iid:04d}'
        with np.load(pd/'partition.npz',allow_pickle=False) as z:
            cc=np.array(z['class_code'],np.uint8); rc=np.array(z['refined_region_code'],np.int32)
        regions=json.loads((pd/'regions.json').read_text())
        # Demo truth raster is reconstructed from state summary only as text; no per-cell
        # truth file is stored by the compact evaluator, so show a blank evaluator panel
        # with counts instead of manufacturing locations.
        blank=np.full(cc.shape+(3,),245,np.uint8)
        p1=panel(base_rgb(cc),f"{s}: integrated partition — {r['object_name']}",f"retained looks={r['retained_fixation_count']} residual={r['integrated_residual_misses']}")
        p2=panel(refined_rgb(rc,regions),'5-degree UNKNOWN shells + explicit micro candidates','pale orange = raw candidate below 25-cell eligibility floor')
        p3=panel(blank,'EVALUATION SUMMARY ONLY',f"eligible positives={r['eligible']['truth_positive_candidate_regions']} recall={r['eligible']['candidate_recall']}")
        canvas=np.hstack((p1,p2,p3)); fn=out/f'frame_{len(frames):02d}.png'; cv2.imwrite(str(fn),canvas); frames.append(fn)
    if frames:
        first=cv2.imread(str(frames[0])); hh,ww=first.shape[:2]; vw=cv2.VideoWriter(str(out/'partition-graph-8b-demo.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),1.5,(ww,hh))
        if vw.isOpened():
            for f in frames: vw.write(cv2.imread(str(f)))
            vw.release()
        thumbs=[cv2.resize(cv2.imread(str(f)),(ww//2,hh//2),interpolation=cv2.INTER_AREA) for f in frames]
        while len(thumbs)%2: thumbs.append(np.full_like(thumbs[0],255))
        cv2.imwrite(str(out/'overview.png'),np.vstack([np.hstack(thumbs[i:i+2]) for i in range(0,len(thumbs),2)]))
    (out/'Demo.md').write_text('# Partition-Graph Phase 8b demo\n\nOne evaluation-side representative per budget scenario. The first two panels are truth-free proposal views; the third reports evaluator counts only. No score, ranking, or policy is shown. Positive pitch is up.\n',encoding='utf-8')
    print(f"[partition-graph8b-demo] wrote {len(frames)} frames to {out}"); return 0
if __name__=='__main__': raise SystemExit(main())
