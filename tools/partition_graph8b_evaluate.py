#!/usr/bin/env python3
"""Offline dense-truth evaluation of Phase-8b budget scenarios."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from fov3d.experiments.classroom_partition.challenge_suite import evaluate_phase8b

def main()->int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source_run"); ap.add_argument("proposal_dir"); ap.add_argument("phase8_evaluation_dir"); ap.add_argument("out_dir")
    a=ap.parse_args(); s=evaluate_phase8b(a.source_run,a.proposal_dir,a.phase8_evaluation_dir,a.out_dir)
    full=next(r for r in s["scenarios"] if r["scenario"]=="full")
    print("[partition-graph8b-evaluate] COMPLETE",json.dumps({"scenarios":s["scenario_count"],"states":s["state_count"],"full_integrated_covered":full["integrated_covered_samples"],"full_integrated_residual":full["integrated_residual_misses"],"full_eligible_recall":full["eligible"]["candidate_recall"]},sort_keys=True)); return 0
if __name__=="__main__": raise SystemExit(main())
