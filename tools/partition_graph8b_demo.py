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

# BGR colours shared by both partition panels (Hershey fonts are ASCII-only).
C_TARGET=(80,190,90)      # green
C_OTHER=(170,130,80)      # steel blue
C_AMBIG=(160,80,190)      # pink
C_TEU=(190,70,190)        # magenta (never present after integration)
C_MICRO=(0,140,255)       # orange: raw candidate below the 25-cell eligibility floor

def _fit(img,text,org,scale,color,maxw):
    while scale>.28 and cv2.getTextSize(text,cv2.FONT_HERSHEY_SIMPLEX,scale,1)[0][0]>maxw: scale-=.01
    cv2.putText(img,text,org,cv2.FONT_HERSHEY_SIMPLEX,scale,color,1,cv2.LINE_AA)

def panel(img,title,footer=''):
    x=np.flipud(np.asarray(img,np.uint8)); x=cv2.resize(x,(W,H-58),interpolation=cv2.INTER_NEAREST)
    out=np.full((H,W,3),248,np.uint8); out[34:34+x.shape[0]]=x
    _fit(out,title,(10,23),.50,(20,20,20),W-16)
    if footer: _fit(out,footer,(10,H-8),.36,(40,40,40),W-16)
    return out

def text_panel(lines,title):
    out=np.full((H,W,3),250,np.uint8)
    _fit(out,title,(10,23),.50,(20,20,20),W-16)
    y=56
    for line in lines:
        if y>H-12: break
        if line: _fit(out,line,(14,y),.42,(30,30,30),W-24)
        y+=22
    return out

def base_rgb(cc):
    out=np.full(cc.shape+(3,),238,np.uint8)
    out[cc==REGION_KIND['TARGET_SUPPORT']]=C_TARGET; out[cc==REGION_KIND['OTHER_SURFACE']]=C_OTHER
    out[cc==REGION_KIND['UNKNOWN']]=(225,225,225); out[cc==REGION_KIND['AMBIGUOUS_BOUNDARY']]=C_AMBIG
    out[cc==REGION_KIND['TARGET_EVIDENCE_UNMAPPED']]=C_TEU; return out

def refined_rgb(rc,regions):
    out=np.full(rc.shape+(3,),238,np.uint8)
    for r in regions:
        m=rc==int(r['region_code']); kind=r['kind']
        if kind=='TARGET_SUPPORT': col=C_TARGET
        elif kind=='OTHER_SURFACE': col=C_OTHER if r['eligible_candidate'] else C_MICRO
        elif kind=='UNKNOWN':
            sh=int(r.get('unknown_shell_index') or 0); v=max(145,240-18*sh); col=(v,v,min(255,v+10)) if r['eligible_candidate'] else C_MICRO
        elif kind=='AMBIGUOUS_BOUNDARY': col=C_AMBIG
        elif kind=='TARGET_EVIDENCE_UNMAPPED': col=C_TEU
        else: col=(175,175,175)
        out[m]=col
    edge=np.zeros(rc.shape,bool); edge[:,1:]|=rc[:,1:]!=rc[:,:-1]; edge[1:,:]|=rc[1:,:]!=rc[:-1,:]
    out[edge&(out!=np.array(C_MICRO,np.uint8)).any(-1)]=(45,45,45)  # keep tiny orange fragments visible
    return out

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
        ss=json.loads((pd/'summary.json').read_text())
        # No per-cell truth file is stored by the compact evaluator, so the third panel
        # reports evaluator counts as text instead of manufacturing truth locations.
        def rec(v): return 'n/a' if v is None else f"{float(v):.3f}"
        def cand(m,label): return f"{label}: {m['candidate_regions']} candidates, {m['truth_positive_candidate_regions']} positive, {m['truth_negative_candidate_regions']} negative"
        e=r['eligible']; bins=e['captured_misses_by_positive_region_area']; lf=e['largest_positive_region_chart_fraction']
        lines=[
            f"{s}: target {iid} {r['object_name']}",
            f"looks retained {r['retained_fixation_count']} of {r['historical_fixation_count']}",
            f"memory stratum {ss['memory_stratum']} (head depth {100*float(ss['head_depth_fraction']):.1f}%)",
            f"reachable {r['reachable_samples']}, covered {r['integrated_covered_samples']}, residual {r['integrated_residual_misses']}",
            "",
            cand(r['raw'],'raw'), f"raw candidate recall {rec(r['raw']['candidate_recall'])}",
            cand(e,'eligible'), f"eligible candidate recall {rec(e['candidate_recall'])}",
            "largest positive region: "+("none" if lf is None else f"{100*float(lf):.1f}% of chart"),
            f"captured by region area <=5%: {bins['le_05']}  5-15%: {bins['05_15']}",
            f"                       15-50%: {bins['15_50']}  >50%: {bins['gt_50']}",
            "",
            "No score / no ranking / no gaze policy",
        ]
        p1=panel(base_rgb(cc),f"{s}: integrated partition - {r['object_name']}",
                 "green=target | blue=other surface | gray=UNKNOWN | pink=ambiguous")
        p2=panel(refined_rgb(rc,regions),'5-degree UNKNOWN shells + explicit micro candidates',
                 "UNKNOWN shells: lighter=0-5 deg from target, darker=farther | orange=<25 cells")
        p3=text_panel(lines,'EVALUATION ONLY: offline truth counts')
        canvas=np.hstack((p1,p2,p3)); fn=out/f'frame_{len(frames):02d}.png'; cv2.imwrite(str(fn),canvas); frames.append(fn)
    if frames:
        first=cv2.imread(str(frames[0])); hh,ww=first.shape[:2]; vw=cv2.VideoWriter(str(out/'partition-graph-8b-demo.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),1.5,(ww,hh))
        if vw.isOpened():
            for f in frames: vw.write(cv2.imread(str(f)))
            vw.release()
        thumbs=[cv2.resize(cv2.imread(str(f)),(ww//2,hh//2),interpolation=cv2.INTER_AREA) for f in frames]
        while len(thumbs)%2: thumbs.append(np.full_like(thumbs[0],255))
        cv2.imwrite(str(out/'overview.png'),np.vstack([np.hstack(thumbs[i:i+2]) for i in range(0,len(thumbs),2)]))
    (out/'Demo.md').write_text('# Partition-Graph Phase 8b demo\n\nOne evaluation-side representative per budget scenario. The first two panels are truth-free proposal views; the third reports evaluator counts only. No score, ranking, or policy is shown. Positive pitch is up.\n\n'
        'Left panel key: green TARGET_SUPPORT; steel blue OTHER_SURFACE; light gray UNKNOWN; pink AMBIGUOUS_BOUNDARY '
        '(magenta TARGET_EVIDENCE_UNMAPPED would appear here but is empty after integration).\n\n'
        'Middle panel key: the same colours, with UNKNOWN split into fixed 5-degree shells by distance from integrated target '
        'support (lighter = nearer, darker = farther) and dark lines at region edges. Orange marks raw candidates below the '
        '25-cell (0.25 deg^2) eligibility floor; they remain represented but are ineligible in the benchmark view.\n\n'
        'Right panel (EVALUATION ONLY): offline truth counts for that state; no truth locations are drawn.\n',encoding='utf-8')
    print(f"[partition-graph8b-demo] wrote {len(frames)} frames to {out}"); return 0
if __name__=='__main__': raise SystemExit(main())
