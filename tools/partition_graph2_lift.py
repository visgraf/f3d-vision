#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from fov3d.experiments.classroom_partition import lift_run

def main() -> int:
    ap = argparse.ArgumentParser(description="Lift a saved Classroom-Oracle-1 run into partition graphs")
    ap.add_argument("run_dir")
    ap.add_argument("out_dir")
    ap.add_argument("--grid-deg", type=float, default=0.10)
    a = ap.parse_args()
    s = lift_run(a.run_dir, a.out_dir, grid_deg=a.grid_deg)
    print("[partition-graph2-lift] COMPLETE", json.dumps(s["aggregate"], sort_keys=True))
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
