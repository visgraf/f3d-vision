"""Scene-level spherical partition representation."""
from .sphere import lonlat_to_unit, unit_to_lonlat, normalize_rows
from .model import (
    BoundaryChain,
    BoundaryKind,
    EyeVisibility,
    FootprintEye,
    ObjectHypothesis,
    ObservationFootprint,
    ObservationOverlay,
    PartitionRegion,
    RegionKind,
    ScenePartitionGraph,
)

__all__ = [
    "BoundaryChain", "BoundaryKind", "EyeVisibility", "FootprintEye",
    "ObjectHypothesis", "ObservationFootprint", "ObservationOverlay",
    "PartitionRegion", "RegionKind", "ScenePartitionGraph",
    "SupportLayer", "joint_owner", "label_joint_regions", "support_depth_from_map",
    "lonlat_to_unit", "unit_to_lonlat", "normalize_rows",
]

# Scene-partition construction needs OpenCV, which Blender's Python lacks.  Resolve it
# on first access so that ``import fov3d.scene`` itself stays OpenCV-free.
_PARTITION_EXPORTS = frozenset(
    {"SupportLayer", "joint_owner", "label_joint_regions", "support_depth_from_map"}
)


def __getattr__(name: str):
    if name in _PARTITION_EXPORTS:
        from . import partition
        return getattr(partition, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
