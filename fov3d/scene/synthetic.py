"""Synthetic occlusion/reappearance fixture for representation tests and demos."""

from __future__ import annotations

import numpy as np

from .model import (
    BoundaryChain,
    BoundaryKind,
    EyeVisibility,
    ObjectHypothesis,
    ObservationFootprint,
    ObservationOverlay,
    PartitionRegion,
    RegionKind,
    ScenePartitionGraph,
)
from .sphere import lonlat_to_unit


def _curve(lon0: float, lon1: float, lat: float, n: int = 9) -> np.ndarray:
    return lonlat_to_unit(np.linspace(lon0, lon1, n), np.full(n, lat))


def build_synthetic_occlusion_case() -> ScenePartitionGraph:
    """Object A appears as two disconnected partition regions around occluder B."""
    regions = {
        "base": PartitionRegion("base", RegionKind.BASE),
        "A-left": PartitionRegion("A-left", RegionKind.OBJECT_COMPONENT, object_id="A"),
        "A-right": PartitionRegion("A-right", RegionKind.OBJECT_COMPONENT, object_id="A"),
        "B": PartitionRegion("B", RegionKind.OBJECT_COMPONENT, object_id="B"),
    }
    objects = {
        "A": ObjectHypothesis("A", ("A-left", "A-right"), {"label": "same-object hypothesis"}),
        "B": ObjectHypothesis("B", ("B",), {"label": "occluder"}),
    }
    boundaries = {
        "a-left-base": BoundaryChain(
            "a-left-base", "A-left", "base", _curve(-18, -7, 2), kind=BoundaryKind.OBJECT_BASE
        ),
        "a-left-b": BoundaryChain(
            "a-left-b", "A-left", "B", _curve(-7, -4, 2), kind=BoundaryKind.OCCLUSION,
            attributes={"front_region": "B", "back_region": "A-left"},
        ),
        "b-a-right": BoundaryChain(
            "b-a-right", "B", "A-right", _curve(4, 7, 2), kind=BoundaryKind.OCCLUSION,
            attributes={"front_region": "B", "back_region": "A-right"},
        ),
        "a-right-base": BoundaryChain(
            "a-right-base", "A-right", "base", _curve(7, 18, 2), kind=BoundaryKind.OBJECT_BASE
        ),
    }
    footprint = ObservationFootprint(
        fixation_id="fix-000",
        eye=EyeVisibility.BINOCULAR,
        polygon_sphere_xyz=lonlat_to_unit(
            np.array([-22, 22, 22, -22]), np.array([-12, -12, 12, 12])
        ),
        gaze_sphere_xyz=lonlat_to_unit(np.array([0.0]), np.array([0.0]))[0],
        sequence_index=0,
        attributes={"source": "synthetic"},
    )
    g = ScenePartitionGraph(
        regions=regions,
        objects=objects,
        boundaries=boundaries,
        observations=ObservationOverlay([footprint]),
        attributes={"fixture": "occlusion_reappearance"},
    )
    g.validate()
    return g
