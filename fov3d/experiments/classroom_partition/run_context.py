"""Historical run context of the Classroom epistemic partition.

Conceptual Core 13 separates the prerecorded experiment's schedule from the intrinsic
epistemic partition. ``fov3d.epistemic.partition`` reports how each surface is known
(``surface_source``, from the current evidence alone). This module adds what the historical
run does with it: ``reconstruction_status`` of an ``OTHER_SURFACE`` region is
``mapped_now`` when the surface is already mapped, and otherwise ``targeted_later`` or
``never_targeted`` according to the experiment's full target list ``all_target_ids``.

The rule is experiment-side on purpose: an autonomous representation cannot know which
objects a prerecorded experiment will target later.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from fov3d.epistemic.partition import build_epistemic_partition


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


def annotate_reconstruction_status(
    region_rows: list[dict[str, Any]],
    *,
    all_target_ids: set[int],
) -> list[dict[str, Any]]:
    """Return the region rows with the historical ``reconstruction_status`` of other surfaces.

    New dictionaries are returned in the same order and the inputs are not modified.
    ``reconstruction_status`` follows ``surface_source``, as in the accepted Core-12
    partition output; rows of other kinds are copied unchanged.
    """
    out = []
    for r in region_rows:
        if r["kind"] == "OTHER_SURFACE" and r["instance_id"] is not None:
            status = (
                "mapped_now" if r["mapped_cells"]
                else "targeted_later" if int(r["instance_id"]) in all_target_ids
                else "never_targeted"
            )
            out.append(_insert_after(r, "surface_source", "reconstruction_status", status))
        else:
            out.append(dict(r))
    return out


def build_run_context_partition(
    state: dict[str, np.ndarray],
    *,
    target_id: int,
    target_name: str,
    all_target_ids: set[int],
    domain: dict[str, Any],
    grid_deg: float,
    gazes_deg: list[tuple[float, float]],
) -> tuple[dict[str, np.ndarray], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Build the intrinsic epistemic partition and apply the historical run context."""
    arrays, region_rows, edge_rows, diag = build_epistemic_partition(
        state,
        target_id=target_id,
        target_name=target_name,
        domain=domain,
        grid_deg=grid_deg,
        gazes_deg=gazes_deg,
    )
    region_rows = annotate_reconstruction_status(region_rows, all_target_ids=all_target_ids)
    return arrays, region_rows, edge_rows, diag
