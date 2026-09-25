#!/usr/bin/env python3
"""Run Partition-Graph Phase 5 head-centred incidental-evidence analysis."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from fov3d.experiments.classroom_partition.incidental import analyze_phase5

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source_run")
    ap.add_argument("lift_dir")
    ap.add_argument("phase4_dir")
    ap.add_argument("out_dir")
    a = ap.parse_args()
    s = analyze_phase5(a.source_run, a.lift_dir, a.phase4_dir, a.out_dir)
    print("[partition-graph5-analyze] COMPLETE", json.dumps({
        "states": len(s["global_states"]),
        "target_gap_violations": s["head_target_depth_true_gap_violations"],
        "challenge_relations": s["challenge_relation_count"],
        "challenge_states": s["challenge_state_count"],
        "challenge_targets": s["challenge_target_count"],
    }, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
