#!/usr/bin/env python3
"""Offline dense-truth evaluation of Phase-8 causal target integration."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from fov3d.experiments.classroom_partition.integration import evaluate_phase8


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source_run")
    ap.add_argument("proposal_dir")
    ap.add_argument("phase7_evaluation_dir")
    ap.add_argument("out_dir")
    a = ap.parse_args()
    s = evaluate_phase8(a.source_run, a.proposal_dir, a.phase7_evaluation_dir, a.out_dir)
    print("[partition-graph8-evaluate] COMPLETE", json.dumps({
        "states": s["state_count"],
        "historical_state_misses": s["prefix_totals"]["historical_missed_state_samples"],
        "cross_target_gain": s["prefix_totals"]["cross_target_integration_gain_state_samples"],
        "own_target_retention_gain": s["prefix_totals"]["own_target_retention_gain_state_samples"],
        "integration_gain": s["prefix_totals"]["integration_gain_state_samples"],
        "residual_state_misses": s["prefix_totals"]["integrated_residual_state_misses"],
        "final_integrated_covered": s["final_prefix_totals"]["integrated_covered"],
        "final_integrated_residual": s["final_prefix_totals"]["integrated_residual"],
        "residual_candidate_recall": s["integrated"]["candidate_recall_on_residual_state_misses"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
