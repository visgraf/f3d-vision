#!/usr/bin/env python3
"""Run Partition-Graph Phase 4 typed-relation analysis."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fov3d.experiments.classroom_partition.relations import analyze_phase4


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source_run", help="accepted Classroom-Oracle-1 full run")
    ap.add_argument("lift_dir", help="fresh Phase-4 joint lift produced with fixed lineage")
    ap.add_argument("out_dir", help="new/empty Phase-4 analysis output")
    args = ap.parse_args()
    s = analyze_phase4(args.source_run, args.lift_dir, args.out_dir)
    print("[partition-graph4-analyze] COMPLETE", json.dumps({
        "states": len(s["global_states"]),
        "target_depth_checks": s["target_depth_valid_validation"]["checks"],
        "target_depth_mismatches": s["target_depth_valid_validation"]["mismatches"],
        "causal_relations": s["causal_final"]["relations"],
        "causal_ownership_cut": s["causal_final"]["ownership_cut"],
        "causal_own_support_gap": s["causal_final"]["own_support_gap"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
