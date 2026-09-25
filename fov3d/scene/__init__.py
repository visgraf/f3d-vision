"""Scene-level spherical partition representation.

This package is intentionally independent of controller policy.  It provides the
representation layer that later active-vision policies may query.
"""

from .sphere import lonlat_to_unit, unit_to_lonlat, normalize_rows
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

__all__ = [
    "BoundaryChain",
    "BoundaryKind",
    "EyeVisibility",
    "ObjectHypothesis",
    "ObservationFootprint",
    "ObservationOverlay",
    "PartitionRegion",
    "RegionKind",
    "ScenePartitionGraph",
    "lonlat_to_unit",
    "unit_to_lonlat",
    "normalize_rows",
]
