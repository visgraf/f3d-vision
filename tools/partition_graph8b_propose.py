#!/usr/bin/env python3
"""Build Phase-8b truth-free budgeted integrated-residual scenarios."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from fov3d.experiments.classroom_partition.challenge_suite import propose_phase8b

def main()->int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source_run"); ap.add_argument("phase5_dir"); ap.add_argument("phase8_proposal_dir"); ap.add_argument("out_dir")
    a=ap.parse_args(); s=propose_phase8b(a.source_run,a.phase5_dir,a.phase8_proposal_dir,a.out_dir)
    print("[partition-graph8b-propose] COMPLETE",json.dumps({"scenarios":s["scenario_count"],"states":s["state_count"],"targets":s["target_count"],"full_phase8_parity":s["full_phase8_parity_checks"],"raw_candidates":s["raw_candidate_region_count"],"eligible_candidates":s["eligible_candidate_region_count"],"truth_used":s["truth_used"]},sort_keys=True)); return 0
if __name__=="__main__": raise SystemExit(main())
