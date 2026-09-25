#!/usr/bin/env python3
"""Offline truth evaluation of Phase-7 prefix proposals."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from fov3d.experiments.classroom_partition.prefix_benchmark import evaluate_phase7


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source_run")
    ap.add_argument("proposal_dir")
    ap.add_argument("phase6_evaluation_dir")
    ap.add_argument("out_dir")
    a = ap.parse_args()
    s = evaluate_phase7(a.source_run, a.proposal_dir, a.phase6_evaluation_dir, a.out_dir)
    print("[partition-graph7-evaluate] COMPLETE", json.dumps({
        "states": s["state_count"],
        "final": s["final_prefix_totals"],
        "local_recall": s["local"]["candidate_recall_over_state_misses"],
        "global_recall": s["global"]["candidate_recall_over_state_misses"],
        "local_2plus_positive_states": s["local"]["states_with_2plus_positive_candidates"],
        "global_2plus_positive_states": s["global"]["states_with_2plus_positive_candidates"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
