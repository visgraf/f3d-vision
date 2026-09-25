#!/usr/bin/env python3
"""Build truth-free causal-final epistemic region proposals for Phase 6."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from fov3d.experiments.classroom_partition.benchmark import propose_phase6

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source_run")
    ap.add_argument("lift_dir")
    ap.add_argument("phase5_dir")
    ap.add_argument("out_dir")
    a = ap.parse_args()
    s = propose_phase6(a.source_run, a.lift_dir, a.phase5_dir, a.out_dir)
    print("[partition-graph6-propose] COMPLETE", json.dumps({
        "targets": s["target_count"],
        "candidate_regions": s["candidate_region_count"],
        "candidate_kinds": s["candidate_kind_counts"],
        "truth_used": s["truth_used"],
    }, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
