#!/usr/bin/env python3
"""Structural/unit checks for Partition-Graph Phase 8b."""
from __future__ import annotations
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from fov3d.experiments.classroom_partition.benchmark import REGION_KIND
from fov3d.experiments.classroom_partition.challenge_suite import (
    BUDGETS, GRID_DEG, MIN_ELIGIBLE_CELLS, UNKNOWN_SHELL_DEG,
    _scenario_look_count, budget_name, memory_stratum, refine_integrated_partition,
)

def main()->int:
    checked=failed=0
    def check(name,cond):
        nonlocal checked,failed; checked+=1; failed+=int(not cond)
        print(f"[partition-graph8b-check] {'PASS' if cond else 'FAIL'} {name}")

    shape=(121,121)
    target=np.zeros(shape,bool); target[59:62,59:62]=True
    other=np.zeros(shape,bool); other[8:11,8:11]=True
    unknown=~(target|other)
    rc=np.zeros(shape,np.int32); rc[target]=1; rc[other]=2; rc[unknown]=3
    cc=np.zeros(shape,np.uint8); cc[target]=REGION_KIND['TARGET_SUPPORT']; cc[other]=REGION_KIND['OTHER_SURFACE']; cc[unknown]=REGION_KIND['UNKNOWN']
    arrays={'region_code':rc,'class_code':cc,'target_support':target,'depth_seen':target|other}
    regions=[
        {'region_code':1,'region_id':'target','kind':'TARGET_SUPPORT','candidate':False,'cell_count':int(target.sum())},
        {'region_code':2,'region_id':'other','kind':'OTHER_SURFACE','candidate':True,'cell_count':int(other.sum()),'instance_id':8,'surface_source':'mapped'},
        {'region_code':3,'region_id':'unknown','kind':'UNKNOWN','candidate':True,'cell_count':int(unknown.sum())},
    ]
    out,rows,edges,diag=refine_integrated_partition(arrays,regions)
    check('all-cells-refined',np.all(out['refined_region_code']>0))
    check('cell-accounting',sum(int(r['cell_count']) for r in rows)==int(np.prod(shape)))
    check('unknown-shells-multiple',len(diag['unknown_shells_present'])>=2)
    tiny=[r for r in rows if r['kind']=='OTHER_SURFACE']
    check('micro-other-preserved',len(tiny)==1 and tiny[0]['cell_count']==9 and tiny[0]['candidate_raw'])
    check('micro-other-ineligible',len(tiny)==1 and not tiny[0]['eligible_candidate'] and MIN_ELIGIBLE_CELLS>9)
    check('large-unknown-eligible',any(r['kind']=='UNKNOWN' and r['eligible_candidate'] for r in rows))
    check('interfaces-present',len(edges)>0 and all(int(e['interface_edge_count'])>0 for e in edges))
    check('budget-domain',BUDGETS==(1,2,4,8,None) and [budget_name(b) for b in BUDGETS]==['budget_1','budget_2','budget_4','budget_8','full'])
    check('budget-cap',_scenario_look_count(3,1)==1 and _scenario_look_count(3,4)==3 and _scenario_look_count(3,None)==3)
    check('memory-strata-domain',memory_stratum(np.zeros((2,2),bool))=='depth_00_25' and memory_stratum(np.ones((2,2),bool))=='depth_75_100')
    check('parameters-fixed',abs(GRID_DEG-.1)<1e-12 and abs(UNKNOWN_SHELL_DEG-5.0)<1e-12 and MIN_ELIGIBLE_CELLS==25)
    check('raw-vs-eligible-explicit',all(('candidate_raw' in r and 'eligible_candidate' in r) for r in rows))
    print(f"[partition-graph8b-check] SUMMARY checked={checked} failed={failed}")
    return 0 if failed==0 else 1
if __name__=='__main__': raise SystemExit(main())
