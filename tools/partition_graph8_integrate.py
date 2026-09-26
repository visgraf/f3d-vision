#!/usr/bin/env python3
"""Build Phase-8 truth-free shadow target-integration proposals for 104 prefixes."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from fov3d.experiments.classroom_partition.integration import propose_phase8


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source_run")
    ap.add_argument("phase5_dir")
    ap.add_argument("phase7_proposal_dir")
    ap.add_argument("out_dir")
    a = ap.parse_args()
    s = propose_phase8(a.source_run, a.phase5_dir, a.phase7_proposal_dir, a.out_dir)
    print("[partition-graph8-integrate] COMPLETE", json.dumps({
        "states": s["state_count"],
        "targets": s["target_count"],
        "phase7_global_parity": s["phase7_global_parity_checks"],
        "target_evidence_unmapped_cells": s["integrated_target_evidence_unmapped_cells_total"],
        "candidate_regions": s["candidate_region_count"],
        "truth_used": s["truth_used"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
