#!/usr/bin/env python3
"""RETIRED: the historical Phase-4 lineage patch tool (tombstone).

This script used to apply a one-shot exact source replacement to
``fov3d/experiments/classroom_partition/joint.py``, repairing the Phase-3 lineage bug
that compared target-local component labels with state-global region codes
(``docs/partition-graph/partition-graph-4-report.md``).

- The Phase-4 lineage fix is already incorporated in accepted code.
- Since Conceptual Core 7 the accepted implementation lives in ``fov3d.scene.lineage``
  (``_lineage``, ``_target_component_raster``), not in ``joint.py``.
- The original repair script is preserved in Git history (added in commit ``52c9395``).

This tombstone performs no source replacement and no repository write. It only prints
the retirement marker and exits 0.
"""
from __future__ import annotations


def main() -> int:
    print("[partition-graph4-lineage-fix] RETIRED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
