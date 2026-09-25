#!/usr/bin/env python3
"""Build Phase-7 local/global causal region proposals for all 104 prefixes."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from fov3d.experiments.classroom_partition.prefix_benchmark import propose_phase7


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source_run")
    ap.add_argument("phase5_dir")
    ap.add_argument("phase6_proposal_dir")
    ap.add_argument("out_dir")
    a = ap.parse_args()
    s = propose_phase7(a.source_run, a.phase5_dir, a.phase6_proposal_dir, a.out_dir)
    print("[partition-graph7-propose] COMPLETE", json.dumps({
        "states": s["state_count"],
        "targets": s["target_count"],
        "local_candidates": s["candidate_region_counts"]["local"],
        "global_candidates": s["candidate_region_counts"]["global"],
        "phase6_final_local_parity": s["phase6_final_local_parity"],
        "truth_used": s["truth_used"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
