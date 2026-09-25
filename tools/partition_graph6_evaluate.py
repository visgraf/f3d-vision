#!/usr/bin/env python3
"""Offline dense-truth evaluation of Phase-6 causal region proposals."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from fov3d.experiments.classroom_partition.benchmark import evaluate_phase6

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source_run")
    ap.add_argument("proposal_dir")
    ap.add_argument("out_dir")
    a = ap.parse_args()
    s = evaluate_phase6(a.source_run, a.proposal_dir, a.out_dir)
    print("[partition-graph6-evaluate] COMPLETE", json.dumps({
        "reachable": s["reachable_samples_total"],
        "covered": s["covered_samples_total"],
        "missed": s["missed_samples_total"],
        "candidate_recall": s["candidate_recall_micro"],
        "truth_positive_candidate_regions": s["truth_positive_candidate_region_count"],
        "miss_components": s["miss_component_count_025deg"],
    }, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
