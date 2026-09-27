"""Historical Classroom candidate interpretation of the epistemic partition.

Conceptual Core 12 separates candidate status from the intrinsic epistemic partition.
``fov3d.epistemic.partition`` describes what is known about each region (its ``kind``,
topology and evidence descriptors). This module holds the historical Partition-Graph
interpretation that calls ``OTHER_SURFACE`` and ``UNKNOWN`` regions candidates.

The rule is experiment-side on purpose: it is the accepted Phase-6/7/8 benchmark
convention, not a general attention policy. Phase 8b keeps its own, distinct
``candidate_raw`` / ``eligible_candidate`` interpretation of refined regions.

Since Conceptual Core 13 the candidate view is composed on the historical run-context
partition (``run_context``), which adds ``reconstruction_status`` to the intrinsic one.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from fov3d.experiments.classroom_partition.run_context import build_run_context_partition


CANDIDATE_KINDS = {"OTHER_SURFACE", "UNKNOWN"}


def _insert_after(mapping: dict[str, Any], anchor: str, key: str, value: Any) -> dict[str, Any]:
    """Copy ``mapping`` with ``key`` inserted immediately after ``anchor``."""
    if key in mapping:
        raise ValueError(f"{key!r} is already present")
    if anchor not in mapping:
        raise KeyError(anchor)
    out: dict[str, Any] = {}
    for k, v in mapping.items():
        out[k] = v
        if k == anchor:
            out[key] = value
    return out


def annotate_candidate_partition(
    region_rows: list[dict[str, Any]],
    diag: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return the historical candidate view of pure partition rows and diag.

    New dictionaries are returned and the inputs are not modified. ``candidate`` follows
    ``kind`` and ``candidate_region_count`` follows ``region_count``, as in the accepted
    Core-11 partition output.
    """
    rows = [
        _insert_after(r, "kind", "candidate", bool(r["kind"] in CANDIDATE_KINDS))
        for r in region_rows
    ]
    out_diag = _insert_after(
        diag, "region_count", "candidate_region_count", sum(bool(r["candidate"]) for r in rows)
    )
    return rows, out_diag


def build_candidate_partition(
    state: dict[str, np.ndarray],
    *,
    target_id: int,
    target_name: str,
    all_target_ids: set[int],
    domain: dict[str, Any],
    grid_deg: float,
    gazes_deg: list[tuple[float, float]],
) -> tuple[dict[str, np.ndarray], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Build the historical run-context partition and apply the historical candidate annotation."""
    arrays, region_rows, edge_rows, diag = build_run_context_partition(
        state,
        target_id=target_id,
        target_name=target_name,
        all_target_ids=all_target_ids,
        domain=domain,
        grid_deg=grid_deg,
        gazes_deg=gazes_deg,
    )
    region_rows, diag = annotate_candidate_partition(region_rows, diag)
    return arrays, region_rows, edge_rows, diag
