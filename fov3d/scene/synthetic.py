"""Synthetic occlusion/reappearance fixture for representation tests and demos."""
from __future__ import annotations

import numpy as np

from .model import (
    BoundaryChain, BoundaryKind, FootprintEye, ObjectHypothesis,
    ObservationFootprint, ObservationOverlay, PartitionRegion, RegionKind,
    ScenePartitionGraph,
)
from .sphere import lonlat_to_unit, normalize_rows


def _curve(lon0: float, lon1: float, lat: float, n: int = 9) -> np.ndarray:
    return lonlat_to_unit(np.linspace(lon0, lon1, n), np.full(n, lat))


def _geom(s: np.ndarray, r: float = 2.0):
    world = r * s
    na = normalize_rows(s + np.array([0.15, 0.0, 0.05]))
    nb = normalize_rows(-s + np.array([0.0, 0.1, 0.05]))
    da = np.full(len(s), r, np.float64)
    db = np.full(len(s), r + 0.4, np.float64)
    return world, na, nb, da, db


def _boundary(bid: str, a: str, b: str, s: np.ndarray, kind: BoundaryKind, **attrs) -> BoundaryChain:
    world, na, nb, da, db = _geom(s)
    return BoundaryChain(
        bid, a, b, s, kind=kind, world_xyz=world, normal_a=na, normal_b=nb,
        depth_a=da, depth_b=db, attributes=attrs,
    )


def build_synthetic_occlusion_case() -> ScenePartitionGraph:
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
        "a-left-base": _boundary("a-left-base", "A-left", "base", _curve(-18, -7, 2), BoundaryKind.OBJECT_BASE),
        "a-left-b": _boundary(
            "a-left-b", "A-left", "B", _curve(-7, -4, 2), BoundaryKind.OCCLUSION,
            front_region="B", back_region="A-left",
        ),
        "b-a-right": _boundary(
            "b-a-right", "B", "A-right", _curve(4, 7, 2), BoundaryKind.OCCLUSION,
            front_region="B", back_region="A-right",
        ),
        "a-right-base": _boundary("a-right-base", "A-right", "base", _curve(7, 18, 2), BoundaryKind.OBJECT_BASE),
    }
    footprint = ObservationFootprint(
        fixation_id="fix-000",
        eye=FootprintEye.BINOCULAR,
        polygon_sphere_xyz=lonlat_to_unit(np.array([-22, 22, 22, -22]), np.array([-12, -12, 12, 12])),
        gaze_sphere_xyz=lonlat_to_unit(np.array([0.0]), np.array([0.0]))[0],
        sequence_index=0,
        attributes={"source": "synthetic"},
    )
    g = ScenePartitionGraph(
        regions=regions, objects=objects, boundaries=boundaries,
        observations=ObservationOverlay([footprint]),
        attributes={"fixture": "occlusion_reappearance", "direction_frame": "synthetic_xyz"},
    )
    g.validate()
    return g
