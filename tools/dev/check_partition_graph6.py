#!/usr/bin/env python3
"""Structural/unit checks for Partition-Graph Phase 6."""
from __future__ import annotations
from pathlib import Path
import sys
import tempfile
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from fov3d.experiments.classroom_partition.benchmark import (
    REGION_KIND, build_epistemic_partition, _covered, _miss_components,
)

def main()->int:
    checked=failed=0
    def check(name,cond):
        nonlocal checked,failed; checked+=1; failed+=int(not cond)
        print(f"[partition-graph6-check] {'PASS' if cond else 'FAIL'} {name}")
    shape=(9,9)
    state={
        "target_support":np.zeros(shape,bool), "owner_instance":np.zeros(shape,np.int32),
        "nearest_instance":np.zeros(shape,np.int32), "ambiguous_instance":np.zeros(shape,bool),
        "depth_seen":np.zeros(shape,bool), "seen_any":np.zeros(shape,bool),
    }
    state["target_support"][3:6,1:3]=True; state["target_support"][3:6,6:8]=True
    state["owner_instance"][4,4]=8; state["depth_seen"][4,4]=True
    state["nearest_instance"][2,4]=9; state["depth_seen"][2,4]=True
    state["ambiguous_instance"][6,4]=True
    state["seen_any"][1:8,1:8]=True
    domain={"yaw":[-0.4,0.4],"pitch":[-0.4,0.4]}
    arrays,regions,edges,diag=build_epistemic_partition(state,target_id=7,target_name="A",all_target_ids={7,8,9},domain=domain,grid_deg=.1,gazes_deg=[(0,0)])
    check("all-cells-classified", np.all(arrays["class_code"]>0) and np.all(arrays["region_code"]>0))
    check("target-components-present", sum(r["kind"]=="TARGET_SUPPORT" for r in regions)==2)
    check("mapped-other-present", any(r["kind"]=="OTHER_SURFACE" and r["instance_id"]==8 and r["mapped_cells"]==1 for r in regions))
    check("incidental-other-present", any(r["kind"]=="OTHER_SURFACE" and r["instance_id"]==9 and r["incidental_cells"]==1 for r in regions))
    check("unknown-candidate-present", any(r["kind"]=="UNKNOWN" and r["candidate"] for r in regions))
    check("ambiguous-not-candidate", all(not r["candidate"] for r in regions if r["kind"]=="AMBIGUOUS_BOUNDARY"))
    check("other-surface-candidate", all(r["candidate"] for r in regions if r["kind"]=="OTHER_SURFACE"))
    check("region-adjacency-symmetric-counted", len(edges)>0 and all(e["interface_edge_count"]>0 for e in edges))
    check("truth-flag-false", diag["truth_used"] is False)

    ref=np.array([[0,0,-1.0],[0.1,0,-1.0]],float); surf=np.array([[0,0,-1.005]],float)
    cov=_covered(ref,surf,.012)
    check("coverage-exact-radius", bool(cov[0]) and not bool(cov[1]))
    comps=_miss_components(np.array([[0,0],[.25,0],[2,2]],float),.25)
    check("miss-components", sorted(map(len,comps))==[1,2])
    check("candidate-kind-domain", all(r["kind"] in REGION_KIND for r in regions))
    print(f"[partition-graph6-check] SUMMARY checked={checked} failed={failed}")
    return 0 if failed==0 else 1

if __name__=="__main__": raise SystemExit(main())
