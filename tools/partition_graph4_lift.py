#!/usr/bin/env python3
"""Run the fixed Partition-Graph joint lift for Phase 4."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fov3d.experiments.classroom_partition.joint import lift_joint_run


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run_dir")
    ap.add_argument("out_dir")
    args = ap.parse_args()
    s = lift_joint_run(args.run_dir, args.out_dir)
    print("[partition-graph4-lift] COMPLETE", json.dumps({
        "states": len(s["global_states"]),
        "evidence_checks": s["controller_seen_any_validation"]["checks"],
        "evidence_mismatches": s["controller_seen_any_validation"]["mismatches"],
        "lineage": s["lineage_totals_excluding_initial"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
